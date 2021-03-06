import os
import json
import requests
import logging, logging.config
import sys

from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from .tokens import account_activation_token
from django.core.mail import EmailMessage

from .models import Greeting, TempUser
from .models import Greeting

from random import randint
from datetime import datetime


LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO'
    }
}

logging.config.dictConfig(LOGGING)

api_key = 'Z1P14W088UZ4E700'
mc_url = 'http://ec2-18-219-67-50.us-east-2.compute.amazonaws.com:8080/dos/api'
json_headers = dict()
json_headers['Content-Type'] = 'application/json;charset=UTF-8'

def register(request):
    if request.method == 'POST':
        data = {
            "email": request.POST.get("email", "yulu9206@gmail.com"),
            "firstName": request.POST.get("firstName", "defaultFirstName"),
            "lastName": request.POST.get("lastName", "defaultLastName"),
            "password": request.POST.get("password", "defaultPassword"),
            "username": request.POST.get("username", "defaultUsername"),
            "role": request.POST.get("role", '1'),
        }
        if data['role'] == '2':
            emailDomain = data['email'].split('@')[1]
            if emailDomain != 'sjsu.edu':
                messages.error(request, 'Admin accound must be registered with SJSU email.')
                return redirect ('/login')
        tempUser = TempUser(email=data['email'], firstName=data['firstName'], lastName=data['lastName'], password=data['password'], username=data['username'], role=data['role'])
        tempUser.save()
        current_site = get_current_site(request)
        mail_subject = 'Activate your movieCentral account.'
        message = render_to_string('acc_active_email.html', {
            'user': tempUser,
            'domain': current_site.domain,
            'uid':tempUser.pk,
            'token':account_activation_token.make_token(tempUser),
        })
        to_email = request.POST.get('email')
        email = EmailMessage(
                    mail_subject, message, to=[to_email]
        )
        email.send()
        return HttpResponse('Please confirm your email address to complete the registration')
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})

def activate(request, uid, token):
    try:
        uid = uid
        user = TempUser.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.isActivate = True
        user.save()
        req_body = {
            "email": user.email,
            "firstName": user.firstName,
            "lastName": user.lastName,
            "password": user.password,
            "username": user.username,
            "role": user.role
        }
        url = mc_url + '/user'
        req_body = json.dumps(req_body)
        res = requests.post(url, data=req_body, headers=json_headers)
        res_body = json.loads(res.content.decode('utf-8'))
        if res.status_code == 201:
            messages.success(request, 'Thank you for your email confirmation. Now you can log in your account.')
        else:
            messages.error(request, res_body['error'])
    else:
        messages.error(request, 'Activation link is invalid!')
    return redirect('/login')

def index(request):
    user = request.session.get('user')
    if user:
        data = {
        'this_user': request.session['user']
        }
        
    else:
        data = {}
    logging.info(data)
    return render(request, 'homepage.html', data)

def profile(request):
    userId = request.session['user']['userId']
    url = mc_url + '/user/' + str(userId)
    res = requests.get(url).json()
    user = res['user']
    data = {
        'user': user,
        'this_user': user
    }
    return render(request, 'profile.html', data)

def editCustomer(request, userId):
    req_body = {
        "email": request.POST.get("email", "yulu9206@gmail.com"),
        "firstName": request.POST.get("firstName", "defaultFirstName"),
        "lastName": request.POST.get("lastName", "defaultLastName"),
        "password": request.POST.get("password", "defaultPassword"),
        "username": request.POST.get("username", "defaultUsername"),
        "city": request.POST.get("city", "defaultcity"),
        "phone": request.POST.get("phone", "defaultphone"),
        "state": request.POST.get("state", "defaultstate"),
        "street": request.POST.get("street", "defaultstreet"),
        "zipcode": request.POST.get("zipcode", "defaultzipcode")
    }

    url = mc_url + '/user/' + userId
    req_body = json.dumps(req_body)
    res = requests.put(url, data=req_body, headers=json_headers)
    res_body = json.loads(res.content.decode('utf-8'))
    if res.status_code == 200:
        messages.success(request, 'Updated')
        request.session['user'] = res_body['user']
    else:
        messages.error(request, res_body['error'])
    return redirect('/profile')

def postEditReview(request, reviewId):
    userId = request.session['user']['userId']
    url = mc_url + '/movie-review/' + str(userId) + '/' + str(reviewId)
    req_body = {
        "comment": request.POST.get("comment", "defaultcomment"),
        "reviewTitle": request.POST.get("reviewTitle", "defaultreviewTitle"),
        "stars": request.POST.get("stars", "defaultstars")
    }
    req_body = json.dumps(req_body)
    res = requests.put(url, data=req_body, headers=json_headers)
    res_body = json.loads(res.content.decode('utf-8'))
    if res.status_code == 200:
        messages.success(request, 'Your reivew has been updated!')
    else:
        messages.error(request, res_body['error'])
    url = mc_url + '/movie-review/' + str(reviewId)
    res = requests.get(url).json()
    movieId = res['Review']['movie']['movieId']
    return redirect('/movie-detail/' + str(movieId))

def sub(request):
    if request.method == 'GET':
        user = request.session['user']
        if user['role'] == 2:
            messages.error(request, 'Admin do not need to subscribe.')
            return redirect('/movies')
        return render(request, 'subscribe.html', {'this_user': user})

    elif request.method == 'POST':
        try:
            this_user = request.session['user']
        except:
            messages.error(request, 'Please log in first!')
            return redirect('/login')
        cardNumber = request.POST.get('cardNumber')
        if not cardNumber:
            messages.error(request, 'Please fill in a valid card number!')
            return redirect('/sub')
        req_body = {
            "subexpiredate": "2019-01-31"
        }
        userId = this_user['userId']
        url = mc_url + '/user/' + str(userId)
        req_body = json.dumps(req_body)
        res = requests.put(url, data=req_body, headers=json_headers)
        res_body = json.loads(res.content.decode('utf-8'))
        if res.status_code == 200:
            request.session['user'] = res_body['user']
            messages.success(request, 'Thank you for subscribing!')
        else:
            messages.error(request, res_body['error'])
        return redirect('/profile')

def addMovie(request):
    req_body = {
        "country": request.POST.get('country', 'defaultCountry'),
        "coverImageUrl": request.POST.get('coverImageUrl', 'defaultUrl'),
        "length": request.POST.get('length', 'defaultLength'),
        "movieDesc": request.POST.get('movieDesc', 'defaultDesc'),
        "movieTitle": request.POST.get('movieTitle', 'defaultTitle'),
        "movie_type": request.POST.get('movie_type', 1),
        "mpaaId": request.POST.get('movieDesc', 1),
        "releaseDate": request.POST.get('releaseDate', '2018-12-05'),
        "studio": request.POST.get('studio', 'defaultStudio'),
        "trailerUrl": request.POST.get('trailerUrl', 'defaultUrl'),
    }
    url = mc_url + '/movie'
    req_body = json.dumps(req_body)
    res = requests.post(url, data=req_body, headers=json_headers)
    res_body = json.loads(res.content.decode('utf-8'))
    print (res_body)
    if res.status_code == 201:
        messages.success(request, 'The Movie is created!')
    else:
        messages.error(request, res_body['error'])
    return redirect('/movies')

def getlogin(request):
    try:
        this_user = request.session['user']
        if this_user:
            messages.info(request, 'You have already logged in.')
        data = {
        'user': this_user
        }
    except:
        data = {}
    return render(request, 'login.html', data)

def login(request):
    req_body = {
        "password": request.POST.get("password", "defaultPassword"),
        "username": request.POST.get("username", "defaultUsername")
    }
    url = mc_url + '/login'
    req_body = json.dumps(req_body)
    res = requests.post(url, data=req_body, headers=json_headers)
    res_body = json.loads(res.content.decode('utf-8'))
    if res.status_code == 200:
        request.session['user'] = res_body['user']
        request.session.get_expire_at_browser_close()
        return redirect('/')
    else:
        messages.error(request, res_body['error'])
        return redirect('/login')

def logout(request):
    del request.session['user']
    return redirect('/')

def customers(request):
    url = mc_url + '/user'
    res = requests.get(url)

    if res.status_code == 200:
        res_body = json.loads(res.content.decode('utf-8'))
        customers = res_body['content']
    else:
        customers = {'defaul': 'default'}
    return render(request, 'customers.html', {'customers': customers, 'user':request.session['user']})

def deleteCustomer(request, userId):
    url = mc_url + '/user/' + userId
    res = requests.delete(url, headers=json_headers)
    res_body = json.loads(res.content.decode('utf-8'))
    if res.status_code == 200:
        messages.success(request, res_body['user'])
    else:
        messages.error(request, res_body['error'])
    return redirect('/customers')

def deleteReview(request, reviewId):
    url = mc_url + '/movie-review/' + reviewId
    res = requests.get(url).json()
    movieId = res['Review']['movie']['movieId']
    res = requests.delete(url, headers=json_headers)
    res_body = json.loads(res.content.decode('utf-8'))
    if res.status_code == 200:
        messages.success(request, 'Your review has been deleted!')
    else:
        messages.error(request, res_body['error'])
    return redirect('/movie-detail/' + str(movieId))

def editReview(request, movieId, reviewId):
    this_review_url = mc_url + '/movie-review/' + reviewId
    this_review = requests.get(this_review_url).json()['Review']

    url_movie = mc_url + '/movie/' + movieId
    url_reviews = mc_url + '/movie-reviews?movieId=' + movieId

    res_movie = requests.get(url_movie).json()
    res_reviews = requests.get(url_reviews).json()

    movie = res_movie['movie']
    reviews = res_reviews['content']
    user = request.session['user']

    for review in reviews:
        starCount = review['stars']
        review['stars'] = 's' * starCount
        review['nostars'] = 'n'* (5 - starCount)

    data = {
        'user': user,
        'movie': movie,
        'reviews': reviews,
        'this_review': this_review
    }

    logging.info(data)

    subexpireMonth = int(user['subexpiredate'].split('-')[1])
    currentMonth = datetime.now().month
    if movie['movie_type'] != 1:
        if subexpireMonth < currentMonth:
            return redirect('/sub/')
    return render(request, 'movieDetail.html', data)
    return

def customerDetail(request, userId):
    url = mc_url + '/user/' + userId
    res = requests.get(url)
    if res.status_code == 200:
        res_body = json.loads(res.content.decode('utf-8'))
        userDetail = res_body['user']
    else:
        userDetail = {'defaul': 'default'}
        messages.error(request, res_body['error'])
    return render(request, 'customerDetail.html', {'userDetail':userDetail})

def movies(request):
    if request.method == 'GET':
        # get-data
        url1 = mc_url + '/movies'
        url2 = mc_url + '/movie-genre/'
        res1 = requests.get(url1).json()
        data = res1['content']
        for i in range(len(data)):
            res2 = requests.get(url2 + str(data[i]['movieId'])).json()
            temp = res2['genres']
            if len(temp) >= 1:
                data[i]['genre'] = temp
            else:
                data[i]['genre'] = ""
        return render(request, 'movies.html', {"data": data, "this_user": request.session['user']})
    if request.method == 'POST':
        # logging.info(request.POST.get('title'))
        title = request.POST.get('title')
        genre = request.POST.getlist('genre')
        desc = request.POST.get('desc')

        url1 = mc_url + '/movies'
        url2 = mc_url + '/movie-genre/'
        res1 = requests.get(url1).json()
        data = res1['content']
        for i in range(len(data)):
            res2 = requests.get(url2 + str(data[i]['movieId'])).json()
            temp = res2['genres']
            if len(temp) >= 1:
                data[i]['genre'] = temp
            else:
                data[i]['genre'] = ""
        toreturn = []
        for d in data:
            gen = []
            flag = False
            for g in d['genre']:
                gen.append(g['genreName'])
            if title in d['movieTitle'] and desc in d['movieDesc']:
                for g in genre:
                    if g not in gen:
                        flag = True
            else:
                flag = True
            if not flag:
                toreturn.append(d)

        return render(request, 'movies.html', {"data":toreturn, "this_user":request.session['user']})

def movieDetail(request, movieId):
    url_movie = mc_url + '/movie/' + movieId
    url_review = mc_url + '/movie-reviews?movieId=' + movieId

    res_movie = requests.get(url_movie).json()
    res_review = requests.get(url_review).json()

    movie = res_movie['movie']
    reviews = res_review['content']
    user = request.session['user']

    for review in reviews:
        starCount = review['stars']
        review['stars'] = 's' * starCount
        review['nostars'] = 'n'* (5 - starCount)

    data = {
        'this_user': user,
        'user': user,
        'movie': movie,
        'reviews': reviews
    }
    if movie['movie_type'] == 1 or user['role']== 2:
        return render(request, 'movieDetail.html', data)
    if user and user['subexpiredate']:
        subexpiredate = user['subexpiredate'].split('-')
        sYear = int(subexpiredate[0])
        sMonth = int(subexpiredate[1])
        sDate = int(subexpiredate[2])
        currentDate = datetime.now()
        year = currentDate.year
        month = currentDate.month
        date = currentDate.date
        if sYear > year or (sYear == year and sMonth > month) or (sYear == year and sMonth == month and sDate > date):
            return render(request, 'movieDetail.html', data)
    return redirect('/sub/')

def postReview(request, movieId):
    url = mc_url + '/movie-review'
    req_body = {
        "comment": request.POST.get("comment", "defaultcomment"),
        "movieId": movieId,
        "reviewTitle": request.POST.get("reviewTitle", "defaultreviewTitle"),
        "stars": request.POST.get("stars", "defaultstars"),
        "userId": request.session['user']['userId']
    }
    req_body = json.dumps(req_body)
    res = requests.post(url, data=req_body, headers=json_headers)
    res_body = json.loads(res.content.decode('utf-8'))
    if res.status_code == 201:
        messages.info(request, "Your review has been submitted!")
    else:
        messages.error(request, res_body['error'])
    return redirect('/movie-detail/' + movieId)

def reports(request):
    url1 = mc_url + '/movies'
    url2 = mc_url + '/movie-genre/'
    res1 = requests.get(url1).json()
    data = res1['content']
    for i in range(len(data)):
        res2 = requests.get(url2 + str(data[i]['movieId'])).json()
        temp = res2['genres']
        if len(temp) >= 1:
            data[i]['genre'] = temp[0]['genreName']
        else:
            data[i]['genre'] = ""
        # placeholder movieplay counts
        d = randint(0,3)
        w = randint(d, d+10)
        m = randint(w, w+20)
        data[i]['lastday_play'] = d
        data[i]['lastweek_play'] = w
        data[i]['lastmonth_play'] = m
    return render(request, 'reports.html', {"data":data, "this_user": request.session['user']})

def customerHistory(request, userId):
    url = mc_url + '/user/' + userId
    res = requests.get(url).json()
    target = res['user']

    # placeholder data
    history = {"dates": ['2018-11-10', '2018-10-29', '2018-10-27'], 'times': [3,5,4]}
    return render(request, 'history.html', {"target": target, "history": history, "this_user": request.session['user']})

def topten(request):
    # placeholder data
    lastday = {"id":[21,1,2,3,4,10,20,26,27,28], "counts":[5,3,2,1,0,0,0,0,0,0]}
    lastweek = {"id":[29,10,21,1,2,3,4,10,20,26], "counts":[13,8,6,3,2,1,0,0,0,0]}
    lastmonth = {"id":[30,4,3,1,2,29,10,21,20,26], "counts":[30,28,20,19,18,13,8,6,0,0]}

    return render(request, "topten.html", {"this_user": request.session['user'],
                                            "day": lastday,
                                            "week": lastweek,
                                            "month": lastmonth})

def financial(request):
    # placeholder data
    payperview =    [2,3,2,5,4,1,1,3,4,4,2,0]
    active =        [4,6,5,8,10,5,5,7,9,6,4,2]
    rest =          [4,6,11,7,5,3,3,2,2,1,1,1]
    ppv_i = []
    for i in payperview:
        ppv_i.append(i*5)
    sub_i = [20,30,30,20,10,10,10,10,0,0,0,0]
    total_i = []
    for i in range(12):
        total_i.append(ppv_i[i] + sub_i[i])
    month = []
    m = datetime.now().month
    for i in range(12):
        if (m+i)%12 == 0:
            month.append(12)
        else:
            month.append(12 - (m+i)%12)
    return render(request, "financial.html", {"this_user": request.session['user']
                                            , "ppv":payperview
                                            , "active": active
                                            , "rest": rest
                                            , "month": month
                                            , "ppv_i": ppv_i
                                            , "sub_i": sub_i
                                            , "total_i": total_i})

def edit(request, movieId = ''):
    if request.method == 'GET':
        if movieId == '':
            url1 = mc_url + '/movies'
            url2 = mc_url + '/movie-genre/'
            res1 = requests.get(url1).json()
            data = res1['content']
            for i in range(len(data)):
                res2 = requests.get(url2 + str(data[i]['movieId'])).json()
                temp = res2['genres']
                if len(temp) >= 1:
                    data[i]['genre'] = temp
                else:
                    data[i]['genre'] = ""
            return render(request, 'edit.html', {"data": data, "this_user": request.session['user']})
        else:
            url = mc_url + '/movie/' + str(movieId)
            res = requests.get(url).json()
            # logging.info(res['movie'])
            return render(request, 'edit.html', {"movie": res['movie'], "this_user": request.session['user']})
    if request.method == 'POST':
        id = request.POST.get('movieid')
        payload = { "country": request.POST.get('country'), "coverImageUrl": request.POST.get('imgurl'), "length": request.POST.get('length'),
                    "movieDesc": request.POST.get('desc'),
                    "movieTitle": request.POST.get('title'),
                    "movie_type": request.POST.get('type'),
                    "mpaaId": request.POST.get('mpaa'),
                    "releaseDate": request.POST.get('releasedate'),
                    "studio": request.POST.get('studio'),
                    "trailerUrl": request.POST.get('trailer') }
        payload = json.dumps(payload)
        url = mc_url + '/movie/' + str(id)
        r = requests.put(url, data=payload, headers=json_headers)
        if (r.status_code == 200):
            messages.success(request, 'Updated!')
        else:
            messages.error(request, 'Update failed!')
        return redirect('/edit/' + str(id))

def toptenwatching(request):
    lastmonth = {"id":[30,4,3,1,2,29,10,21,20,26], "counts":[30,28,20,19,18,13,8,6,0,0]}
    url1 = mc_url + '/movies'
    res1 = requests.get(url1).json()
    data = res1['content']

    toreturn = []
    for i in lastmonth['id']:
        for j in data:
            if j['movieId'] == i:
                toreturn.append(j)
    return render(request, 'toptenwatching.html', {"this_user": request.session['user'], "lastmonth": lastmonth, "movies": toreturn})

def delete(request, movieId):
    url = mc_url + '/movie/' + str(movieId)
    logging.info(url)
    data = {"movieId": movieId}
    data = json.dumps(data)
    r = requests.delete(url, headers=json_headers, data=data)
    if r.status_code == 200:
        messages.success(request, 'Deleted!')
    else:
        messages.error(request, 'Deletion failed!')
    url1 = mc_url + '/movies'
    url2 = mc_url + '/movie-genre/'
    res1 = requests.get(url1).json()
    data = res1['content']
    for i in range(len(data)):
        res2 = requests.get(url2 + str(data[i]['movieId'])).json()
        temp = res2['genres']
        if len(temp) >= 1:
            data[i]['genre'] = temp
        else:
            data[i]['genre'] = ""
    return redirect('/edit', {"data": data, "this_user": request.session['user']})
  
def topTenRating(request):
    url = mc_url + '/movie-reviews/'
    res = requests.get(url).json()
    reviews = res['content']
    reviews = sorted(reviews, key=lambda review: review['stars'], reverse=True)
    for review in reviews:
        starCount =  int(review['stars'])
        review['stars'] = 's' * starCount
        review['nostars'] = 'n' * (5 - starCount)
    data = {
        'reviews':reviews,
        'this_user': request.session['user']
    }
    return render(request, 'topTenRating.html', data)
