#coding=utf-8
#baidu ai easydl toolkit by kooky126
import urllib.request
import configparser
import os
import json
import re
import time
import base64
import cv2
import glob
from xml.etree import ElementTree as ET

#初始化token
def inittoken():
	cf = configparser.ConfigParser()
	a = cf.read("easydl.conf")
	print(a)
	client_id = cf.get("token","client_id")
	print(client_id)
	client_secret = cf.get("token","client_secret")
	host = 'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id='+client_id+'&client_secret='+client_secret
	request = urllib.request.Request(host)
	request.add_header('Content-Type', 'application/json; charset=UTF-8')
	response = urllib.request.urlopen(request)
	content = response.read()
	if (content):
		date = json.loads(content.decode('utf-8'))
		if date['access_token']:
			with open("token.json","w") as f:
				json.dump(date,f)
			return date['access_token']
		else:
			return None
	else:
		return None

#取token
def gettoken():
	if os.path.exists('token.json'):
		with open('token.json') as f:
			data = json.load(f)
			expires = int(re.findall(r"\d{10}",data['access_token'])[0])
			if expires>int(time.time()):
				return data['access_token']
			else:
				return inittoken()
	else:
		return inittoken()

#缩小图像，长宽不超过max
def resize(img,max):
	heigth,width,_ = img.shape
	scale = 1.0
	if heigth>max or width>max:
		if heigth>width:
			nh = max
			scale = max/heigth
			nw = int(width*scale)
		else:
			nw = max
			scale = max/width
			nh = int(heigth*scale)
		return  cv2.resize(img, (nw,nh), interpolation=cv2.INTER_CUBIC),scale
	else:
		return img,scale

#增加单个样本
#dataset_id：easydl数据集id
#imgfile：图片文件路径
#xmlfile：标记xml文件路径
#name文件名：导入后平台显示的图片文件名，不要带jpg后缀
#max：max大于0且长或宽超过max时，会缩放图片，max为0时不缩放，保留原图
#append：easydl api里的参数，通常False就行
def addentity(dataset_id,imgfile,xmlfile,name,max=0,append=False):
	request_url = "https://aip.baidubce.com/rpc/2.0/easydl/dataset/addentity"
	access_token = gettoken()
	if not access_token is None:
		request_url = request_url + "?access_token=" + access_token
		scale = 1
		image = cv2.imread(imgfile)
		if max>0:
			image,scale = resize(image,max)
		h, w =image.shape[:2]
		_,buffer = cv2.imencode('.jpg', image)
		jpg64 = base64.b64encode(buffer)
		jpg_as_text = jpg64.decode("utf-8")
		req = {}
		req['entity_content']=jpg_as_text
		req['type'] = "OBJECT_DETECTION"
		req['dataset_id'] = dataset_id
		req['appendLabel'] = append
		req['entity_name'] = name+".jpg"
		tree = ET.parse(xmlfile)
		root = tree.getroot()
		objects = root.findall("object")
		subobjs = []
		for object in objects:
			name = object.find("name").text
			xmin = int(int(object.find("bndbox").find("xmin").text)*scale)
			ymin = int(int(object.find("bndbox").find("ymin").text)*scale)
			xmax = int(int(object.find("bndbox").find("xmax").text)*scale)
			ymax = int(int(object.find("bndbox").find("ymax").text)*scale)
			subobject = {}
			subobject['label_name'] = name
			subobject['left'] = xmin
			subobject['top'] = ymin
			subobject['width'] = int(xmax-xmin)
			subobject['height'] = int(ymax-ymin)
			subobjs.append(subobject)
		req['labels']=subobjs
		params = bytes(json.dumps(req),"utf8")
		request = urllib.request.Request(url=request_url, data=params)
		request.add_header('Content-Type', 'application/json')
		response = urllib.request.urlopen(request)
		content = response.read()
		data = json.loads(content.decode('utf-8'))
		return data
	else:
		return None

#批量增加样本
#dataset_id：easydl数据集id
#path：lableImg的数据目录
#max：max大于0且长或宽超过max时，会缩放图片，max为0时不缩放，保留原图
#append：easydl api里的参数，通常False就行
def addentitybatch(dataset_id,path,max=0,append=False):
	if os.path.exists(path):
		xmlfiles = glob.glob(os.path.join(path,"*.xml"))
		for xmlfile in xmlfiles:
			dir,xmlfilename = os.path.split(xmlfile)
			name,_=os.path.splitext(xmlfilename)
			imgfile = xmlfile.replace("xml","jpg")
			res = addentity(dataset_id,imgfile,xmlfile,name,max,append)
			if not res is None:
				if "error_msg" in res:
					print("ERROR",res['error_msg'],xmlfile)
				else:
					print("OK",xmlfile)
