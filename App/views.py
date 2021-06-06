from django.shortcuts import render,redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponseNotFound
from faunadb import query as q
import pytz
from faunadb.objects import Ref
from faunadb.client import FaunaClient
import hashlib
import datetime
import tweepy
from django.http import JsonResponse
import json



client = FaunaClient(secret="fauna_secret_key")
api_key = "api_key"
api_secret = "api_secret"
access_token = "access_token"
access_token_secret= "access_token_secret"
username= "username"
screen_name=username

auth = tweepy.OAuthHandler(api_key, api_secret)

auth.set_access_token(access_token, access_token_secret)

api = tweepy.API(auth)
user=api.me()
# Create your views here.
def index(request):
    tmpTweets = api.user_timeline(screen_name=username,count=100, include_rts = True)
    today = endDate = datetime.datetime.now()
    startDate = today - (datetime.timedelta(today.weekday() + 1))

    tweets=[]
    new_followers=0
    words=[]
    all_trends = set()
    COUNTRY_WOE_ID = 23424908

    country_trends = api.trends_place(COUNTRY_WOE_ID)

    trends = json.loads(json.dumps(country_trends, indent=1))

    for trend in trends[0]["trends"]:
        all_trends.add((trend["name"].lower().replace("#","")))

    for tweet in tmpTweets:
        if endDate >= tweet.created_at >= startDate:
            tweets.append(tweet)
            words.extend(set(tweet.text.lower().split()) & all_trends)

    tweeted_keywords=(sorted([(i, words.count(i)) for i in set(words)], key=lambda x: x[1], reverse=True))

    try:
        previous_follower = client.query(q.get(q.match(q.index("followers_index"), True)))
        previous_follower_count = client.query(q.get(q.match(q.index("followers_index"), True)))["data"]["follower_count"]
    except:
        follower_count_create = client.query(q.create(q.collection("Followers"),{
            "data": {
                "follower_count": user.followers_count,
                "created_at": datetime.datetime.now(pytz.UTC),
                "status":True
            }
        }))
        previous_follower_count=user.followers_count

    new_followers=user.followers_count-previous_follower_count

    if previous_follower_count == user.followers_count:
        pass
    else:
        follower_count_update = client.query(q.update(q.ref(q.collection("Followers"), previous_follower["ref"].id()), {
            "data": {
                "follower_count": user.followers_count,
                "created_at": datetime.datetime.now(pytz.UTC),
                "status":True,
            }
        }))
    if request.method=="POST":
        generate=request.POST.get("generated")
        report_date= datetime.datetime.now(pytz.UTC)
        report_details = "Number of followers :"+str(user.followers_count) + "\n Number following :"+str(user.friends_count) + "\n Number of Tweets This Week :"+str(len(tweets)) +  "\n New Followers: "+str(new_followers)+ "\n Trends You Tweeted On:"+str(tweeted_keywords)
        if generate == "True":
            report_create = client.query(q.create(q.collection("TweetsReport"), {
                "data": {
                    "report_date": report_date,
                    "report_details": report_details,
                    "status": True
                }
            }))

    context={"followers":user.followers_count,"following":user.friends_count,"weekly_tweet":len(tweets),"new_followers":new_followers}
    return render(request,"index.html",context)


def reports(request):
    get_reports= client.query(q.paginate(q.match(q.index("report_index"), True)))
    all_reports=[]
    for i in get_reports["data"]:
        all_reports.append(q.get(q.ref(q.collection("TweetsReport"),i.id())))
    reports=client.query(all_reports)
    context={"reports":reports}
    return render(request,"reports.html",context)
