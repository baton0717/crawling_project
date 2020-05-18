from flask import Flask, render_template, request, session, redirect
import re
import os
import requests
from bs4 import BeautifulSoup
import pymysql
from datetime import date, timedelta
from konlpy.tag import Kkma
from selenium import webdriver
import base64

app = Flask(__name__, template_folder='templates')
app.env = 'development'
app.debug = True
app.secret_key = '1q2w3e4r'
kkma = Kkma()

db = pymysql.connect(
    user='root',
    passwd='dw',
    db='web',
    host='localhost',
    charset='utf8',
    cursorclass=pymysql.cursors.DictCursor
)

def get_menu():
    cursor = db.cursor()
    cursor.execute("select id, title from topic order by title desc")
    return cursor.fetchall()


@app.route('/')
def index():
    cursor = db.cursor()
    cursor.execute("select id, title from topic order by title desc")
    return render_template('index.html', 
                            user=session.get('user'))

# session을 활용하여 로그인 기능을 구현한다. 
# index 페이지 
# 로그인이 안되어있을 때에는 로그인, 회원가입 링크를 보여주고,
# 로그인이 되어있을 때에는 로그아웃, 회원탈퇴 링크를 보여준다.
# 회원로그인 /login, 회원로그아웃 /logout 
# 회원가입 /join, 회원탈퇴 /withdrawal

@app.route('/join', methods=['get', 'post'])
def join():
    #insert 문으로 DB에 회원정보 추가하기
    if request.method == 'GET':
        return render_template('join.html')
    cursor = db.cursor()
    cursor.execute(f"""
        insert into author (name, profile, password)
        values ('{ request.form['userid'] }', '{ request.form['profile'] }',  SHA2('{ request.form['password'] }', 256))
    """)
    db.commit()
 
    return redirect('/')


@app.route('/<cid>')
def content(cid):
    cursor = db.cursor()
    cursor.execute(f"""
        select id, title, description, created, author_id from topic
        where id = '{ cid }'
    """)
    content = cursor.fetchone()
    return render_template('template.html', menu=get_menu(), content=content)

@app.route('/login', methods=['get', 'post'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    cursor = db.cursor()
    cursor.execute(f"""
        select id, name, profile from author
        where name = '{ request.form['userid'] }' and
              password = SHA2('{ request.form['password'] }', 256)
    """)
    user = cursor.fetchone()
    if user:
        session['user'] = user
        return redirect('/')
    else:
        return render_template('login.html', msg="로그인 정보를 확인하세요")

@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/')

@app.route('/withdrawal')
def withdrawal():
    deluser = session.pop('user')
    cursor = db.cursor()
    cursor.execute(f"""
    delete from author where name = '{deluser['name']}'
    """)
    db.commit()
    return redirect('/')


# /news/ranking 
# 다음 랭킝 뉴스 크롤링 - https://media.daum.net/ranking/
# 날짜를 입력받는 폼을 보여주고, 날짜를 입력하고 버튼을 클릭하면 해당 날짜의 뉴스 랭킹 리스트를 보여준다. 
# 뉴스의 리스트 url은 다음과 같이 한다. "/news/words?url=<해당뉴스의 url>"

def get_news():
    date_1=request.form['date']
    regDate = date_1.replace('-','')
    query = {'regDate' : regDate }
    url = 'https://media.daum.net/ranking/'
    res = requests.get(url,params=query)
    soup = BeautifulSoup(res.content, 'html.parser')
    newses = [dict(
        title=tag.get_text(),
        urls=tag['href']
                ) for tag in soup.select('.tit_thumb > a')]
    return newses
@app.route('/news/ranking', methods=['get', 'post'])
def ranking():
    if request.method == 'GET':
        return render_template('ranking.html')
    


    # for i in soup.select('.tit_thumb'):
    #     print(i)
    
    news_a = get_news()
    return render_template('ranking.html', soup=news_a)


@app.route('/news/words', methods=['get', 'post'])
def words():
    if request.method == 'GET':
        return render_template('words.html')
    news = get_news()
    print(news)
    for url in news['urls']:
        query = {'url' : url }
    

    return render_template('words.html', soup=query)

#/downloads/<검색어>
# 다음 구글 이미지 크롤링
# 키워드로 검색된 구글 이미지를 디렉토리에 다운로드한다.
# url로 불러오는 경우와 바이너리가 직접 들어있는 경우 모두 다운로드한다.


@app.route('/downloads/<keyword>', methods=['get', 'post'])
def downloads(keyword):

    if request.method == 'GET':
        return render_template('down.html', keyword = keyword)

    driver = webdriver.Chrome('chromedriver')
    driver.implicitly_wait(3)


    url = f'https://www.google.com/search?q={keyword}&tbm=isch'
    
    

    driver.get(url)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

 
    
    img_links = [ tag.get('src') for tag in soup.select('img.rg_i')]
    print(img_links[20])

    

    #디렉토리 생성
    os.makedirs(f'static/download2/{keyword}',exist_ok=True)

    

    #다운로드
    for i, link in enumerate(img_links):
        if str(link[:4]) == 'data':
            imgdata = base64.b64decode(link.split(',')[1])
            with open(f'static/download2/{keyword}/{i}.jpg', 'wb') as f:
                f.write(imgdata)
            
        else:
            res = requests.get(link)
            with open(f'static/download2/{keyword}/{i}.jpg', 'wb') as f:
                f.write(res.content)


    return render_template('down.html', img_links=img_links, keyword = keyword)





app.run()