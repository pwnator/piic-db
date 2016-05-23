from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.mail import get_connection, EmailMessage, send_mail
from django.db import connection, models
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, get_object_or_404, render_to_response
from django.template import RequestContext
from django import forms
from docx import Document
from docx.shared import Pt
from math import floor
from plotter.models import *
import binascii, datetime, hashlib, json, os, requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testplot.settings')

class SimpleFileForm(forms.Form):
	template = forms.Field(widget=forms.FileInput, required=False)

def user_login(request):
	context=RequestContext(request)
	if request.method == 'POST':
		username = request.POST['username']
		password = request.POST['password']
		user = authenticate(username=username, password=password)
		if user:
			if user.is_active:
				login(request, user)
				return HttpResponseRedirect('/')
			else:
				return HttpResponse("This account is disabled.")
		else:
			return render(request, 'plotter/login.html', {'invalid': True})
	else:
		return render(request, 'plotter/login.html', {'required': True})

@login_required
def user_logout(request):
	logout(request)
	return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def index(request):
	context_dict = {
		'students' : Participant.objects.filter(trainees__in=Training.objects.all()).distinct().filter(designation__contains='BS'),
		'masters' : Participant.objects.filter(trainees__in=Training.objects.all()).distinct().filter(designation__startswith='MS'),
		'faculty' : Participant.objects.filter(trainees__in=Training.objects.all()).distinct().filter(Q(designation__contains='Faculty')|Q(designation__contains='Lecturer')),
		'engineers' : Participant.objects.filter(trainees__in=Training.objects.all()).distinct().filter(designation__contains='Engineer'),
		'total' : Participant.objects.filter(trainees__in=Training.objects.all()).distinct(),
		'employed' : Participant.objects.exclude(company__isnull=True).exclude(company__exact=''),
		'instns': Institution.objects.order_by('abbrev'),
		'years' : Training.objects.order_by('year').values('year').distinct(),
		'modules' : Module.objects.order_by('topic', 'version'),
		'abbrevs' : Module.objects.order_by('topic').values('topic').distinct(),
		'graddates' : Participant.objects.order_by('graddate').values('graddate').distinct()
	}
	return render(request, 'plotter/index.html', context_dict)

@login_required
def chart1a(request, year):
	cursor = connection.cursor()
	cursor.execute('SELECT topic,COUNT(*) FROM plotter_module,plotter_training WHERE year=%s AND plotter_module.ID=plotter_training.module_id GROUP BY topic', [year])
	results = cursor.fetchall()
	return JsonResponse(dict(results))

@login_required
def chart1b(request, year):
	cursor = connection.cursor()
	cursor.execute('SELECT topic,COUNT(participant_id) FROM plotter_module,plotter_training,plotter_training_trainee WHERE year=%s AND plotter_module.ID=plotter_training.module_id AND training_id=plotter_training.ID GROUP BY topic', [year])
	results = cursor.fetchall()
	return JsonResponse(dict(results))

@login_required
def chart2a(request, year):
	cursor = connection.cursor()
	cursor.execute('SELECT abbrev,COUNT(*) FROM plotter_institution,plotter_participant WHERE plotter_participant.ID IN (SELECT participant_id FROM plotter_training_trainee WHERE training_id IN (SELECT ID FROM plotter_training WHERE year=%s)) AND plotter_institution.ID=plotter_participant.instn_id GROUP BY abbrev', [year])
	results = cursor.fetchall()
	return JsonResponse(dict(results))

@login_required
def chart2b(request, year):
	cursor = connection.cursor()
	cursor.execute('SELECT designation,COUNT(participant_id) FROM plotter_training,plotter_training_trainee,plotter_participant WHERE year=%s AND participant_id=plotter_participant.ID AND training_id=plotter_training.ID GROUP BY designation', [year])
	results = cursor.fetchall()
	return JsonResponse(dict(results))

@login_required
def chart3(request, instn_id):
	cursor = connection.cursor()
	results = []
	cursor.execute('SELECT DISTINCT topic,training_id,version,date FROM plotter_institution, plotter_institution_module, plotter_module, plotter_participant, plotter_training, plotter_training_trainee WHERE plotter_training_trainee.participant_id=plotter_participant.ID AND plotter_training_trainee.training_id=plotter_training.ID AND plotter_training.module_id=plotter_module.ID AND plotter_participant.instn_id=%s ORDER BY date', [instn_id])	
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	return JsonResponse(results, safe=False)

@login_required
def chart4(request, date):
	cursor = connection.cursor()
	cursor.execute('SELECT location,plotter_training.ID as training_id,topic,version,date FROM plotter_training,plotter_module WHERE plotter_training.date>=%s AND plotter_training.date<%s AND plotter_training.module_id=plotter_module.ID ORDER BY date', [date, str(int(date)+100)])
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	return JsonResponse(results, safe=False)

@login_required
def chart5(request, instn_id):
	cursor = connection.cursor()
	cursor.execute('SELECT DISTINCT T1.participant_id AS participant_id,(T1.score*0.4+T2.score*0.6) AS final,T1.sname AS sname,T1.fname AS fname,T1.training_id AS training_id,T1.topic AS topic FROM (SELECT score,training_id,participant_id,sname,fname,topic FROM plotter_activity,plotter_participant,plotter_training,plotter_module WHERE plotter_activity.participant_id=plotter_participant.ID AND training_id=plotter_training.ID AND plotter_training.module_id=plotter_module.ID AND category="Quiz" AND instn_id=%s) AS T1 LEFT JOIN (SELECT score,training_id,participant_id FROM plotter_activity,plotter_participant,plotter_training WHERE plotter_activity.participant_id=plotter_participant.ID AND training_id=plotter_training.ID AND category="Lab" AND instn_id=%s) AS T2 ON T1.training_id=T2.training_id AND T1.participant_id=T2.participant_id ORDER BY final DESC LIMIT 12', [instn_id, instn_id])
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	return JsonResponse(results, safe=False)

@login_required
def chart6(request, mod_id):
	cursor = connection.cursor()
	cursor.execute('SELECT DISTINCT(T1.participant_id) AS participant_id,(T1.score*0.4+T2.score*0.6) AS final,T1.sname AS sname,T1.fname AS fname,T1.abbrev AS abbrev,T1.instn_id AS instn_id FROM (SELECT score,training_id,participant_id,sname,fname,abbrev,instn_id FROM plotter_activity,plotter_participant,plotter_training,plotter_institution WHERE plotter_activity.participant_id=plotter_participant.ID AND training_id=plotter_training.ID AND plotter_participant.instn_id=plotter_institution.ID AND category="Quiz" AND module_id=%s) AS T1 LEFT JOIN (SELECT score,training_id,participant_id FROM plotter_activity,plotter_participant,plotter_training WHERE plotter_activity.participant_id=plotter_participant.ID AND training_id=plotter_training.ID AND category="Lab" AND module_id=%s) AS T2 ON T1.training_id=T2.training_id AND T1.participant_id=T2.participant_id ORDER BY final DESC LIMIT 12', [mod_id, mod_id])
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	return JsonResponse(results, safe=False)

@login_required
def chart7(request, topic, graddate):
	cursor = connection.cursor()
	cursor.execute('SELECT abbrev,COUNT(*) FROM plotter_participant,plotter_training,plotter_training_trainee,plotter_module,plotter_institution WHERE plotter_training_trainee.training_id=plotter_training.ID AND plotter_training_trainee.participant_id=plotter_participant.ID AND plotter_training.module_id=plotter_module.ID AND plotter_participant.instn_id=plotter_institution.ID AND topic=%s AND graddate<=%s GROUP BY abbrev', [topic, graddate])
	results = cursor.fetchall()
	return JsonResponse(dict(results))

@login_required
def chart8(request, topic, graddate, abbrev):
	cursor = connection.cursor()
	cursor.execute('SELECT fname,sname,plotter_participant.ID AS ppant_id,designation,graddate FROM plotter_participant,plotter_training,plotter_training_trainee,plotter_module,plotter_institution WHERE plotter_training_trainee.training_id=plotter_training.ID AND plotter_training_trainee.participant_id=plotter_participant.ID AND plotter_participant.instn_id=plotter_institution.ID AND plotter_training.module_id=plotter_module.ID AND topic=%s AND graddate<=%s AND abbrev=%s ORDER BY graddate,sname', [topic, graddate, abbrev])
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	return JsonResponse(results, safe=False)

@login_required
def test(request):
	if request.user.username == 'dost':
		return render(request, 'plotter/test.html', {'restricted' : True})
	else:
		return render(request, 'plotter/test.html')

@login_required
def query(request, query):
	if request.user.username == 'dost':
		return HttpResponse("This account has insufficient privileges.")
	else:
		header = query[0:5]
		query = ' '.join(query[5:].split('-'))
		cursor = connection.cursor()
		cursor.execute(query)
		results = []
		col_names = [name[0] for name in cursor.description]
		for row in cursor.fetchall():
			rowset = []
			for col in zip(col_names, row):
				rowset.append(col)
			results.append(dict(rowset))
		return JsonResponse(("</br>".join(str(row) for row in results)), safe=False) if header == 'test/' else JsonResponse(results, safe=False)

@login_required
def asms(request):
	if request.user.username == 'dost':
		return render(request, 'plotter/asms.html', {'trainings' : Training.objects.order_by('-date'), 'instns': Institution.objects.order_by('abbrev'), 'graddates' : Participant.objects.order_by('graddate').values('graddate').distinct(), 'restricted' : True})
	else:
		return render(request, 'plotter/asms.html', {'trainings' : Training.objects.order_by('-date'), 'instns': Institution.objects.order_by('abbrev'), 'graddates' : Participant.objects.order_by('graddate').values('graddate').distinct()})

@login_required
def text(request, ppant_id, ip, message):
	p = Participant.objects.get(pk=ppant_id)
	if "**name**" in message:
		message = message.replace("**name**", p.fname + ' ' + p.sname)
	try:
		r = requests.get('http://' + ip + '/sendsms?phone=0' + str(p.contactn) + '&text=' + message)
	except requests.exceptions.ConnectionError:
		return HttpResponse('error')
	return HttpResponse('sent')

@login_required
def upload(request):
	if request.method == 'POST':
		if 'template' in request.FILES:
			template = request.FILES['template']
			filetype = template.content_type
			if filetype != 'text/html':
				return HttpResponse('File extension not allowed.')
			else:
				dest = open('media/template.html', 'wb+')
				s = b''
				for chunk in template.chunks():
					dest.write(chunk)
					s += chunk
				dest.close()
				return HttpResponse(s)
	else:
		return HttpResponse('No file uploaded.')

@login_required
def mail(request):
	if request.user.username == 'dost':
		return render(request, 'plotter/mail.html', {'trainings' : Training.objects.order_by('-date'), 'instns': Institution.objects.order_by('abbrev'), 'graddates' : Participant.objects.order_by('graddate').values('graddate').distinct(), 'restricted' : True})
	else:
		form = SimpleFileForm()
		return render(request, 'plotter/mail.html', {'trainings' : Training.objects.order_by('-date'), 'instns': Institution.objects.order_by('abbrev'), 'graddates' : Participant.objects.order_by('graddate').values('graddate').distinct(), 'form' : form})

@login_required
def message(request, ppant_id, html, subject, message):
	p = Participant.objects.get(pk=ppant_id)
	connection = get_connection()
	connection.open()
	if html == '1':
		msg = open('media/template.html','r')
		message = msg.read()
		msg.close()
	if "**name**" in message:
		message = message.replace("**name**", p.fname + ' ' + p.sname)
	email = EmailMessage(subject, message, 'contactus@piic.org.ph', [p.email])
	email.content_subtype = 'html'
	email.send()
	connection.close()
	return HttpResponse('sent')

@login_required
def timestamp(request, category, medium, contactn):
	p = Participant.objects.get(contactn=contactn)
	Message.objects.create(participant=p,category=category,medium=medium)
	return HttpResponse()

@login_required
def history(request):
	cursor = connection.cursor()
	cursor.execute('SELECT * FROM plotter_participant ORDER BY datetime(modified) DESC LIMIT 15')
	remarks = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		remarks.append(dict(rowset))
	cursor.execute('SELECT plotter_message.*,plotter_participant.sname,plotter_participant.fname FROM plotter_message,plotter_participant WHERE plotter_message.participant_id=plotter_participant.ID AND medium="text" ORDER BY datetime(timestamp) DESC LIMIT 15')
	texts = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		texts.append(dict(rowset))
	cursor.execute('SELECT plotter_message.*,plotter_participant.sname,plotter_participant.fname FROM plotter_message,plotter_participant WHERE plotter_message.participant_id=plotter_participant.ID AND medium="mail" ORDER BY datetime(timestamp) DESC LIMIT 15')
	mail = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		mail.append(dict(rowset))
	return render(request, 'plotter/history.html', {'remarks' : remarks, 'texts' : texts, 'mail' : mail})

@login_required
def employed(request):
	if request.user.username == 'dost':
		return render(request, 'plotter/employed.html', {'participants' : Participant.objects.filter(employment=True).order_by('instn'), 'micro' : Participant.objects.exclude(company__isnull=True).exclude(company__exact='').order_by('instn'), 'restricted' : True})
	else:
		return render(request, 'plotter/employed.html', {'participants' : Participant.objects.filter(employment=True).order_by('instn'), 'micro' : Participant.objects.exclude(company__isnull=True).exclude(company__exact='').order_by('instn')})

def encrypt(code):
	key = hashlib.pbkdf2_hmac('sha256', code.encode('utf-16be'), b'piic', 10000)
	base = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	serial = []
	key = int.from_bytes(key, byteorder='little')
	while key:
		rem = key % 62
		key = key // 62
		serial.append(base[rem])
	serial.reverse()
	serial = ''.join(serial)[:8]
	return serial

@login_required
def certificate(request, training_id, ppant_id):
	t = Training.objects.get(pk=training_id)
	p = Participant.objects.get(pk=ppant_id)
	document = Document('media/template.docx')
	for paragraph in document.paragraphs:
		for run in paragraph.runs:
			if '<<name>>' in run.text:
				if p.mi: run.text = p.sname + ', ' + p.fname + ' ' + p.mi
				else: run.text = p.sname + ', ' + p.fname
			if '<<module>>' in run.text: run.text = '"' + t.module.fullname + '"'
			if '<<date>>' in run.text:
				startdate = datetime.datetime.strptime(str(t.date), '%Y%m%d')
				enddate = startdate + datetime.timedelta(days=4)
				run.text = 'held from ' + startdate.strftime('%d %B') + ' to ' + enddate.strftime('%d %B %Y') + ' at the '
			if '<<location>>' in run.text:
				l = Institution.objects.get(abbrev=t.location)
				run.text = l.fullname + ', ' + l.city + ', ' + l.province
			if '<<honors>>' in run.text: run.text = ''
			if '<<serial>>' in run.text:
				code = 'participant'+ppant_id+'training'+training_id
				serial = encrypt(code)
				run.text = 'Serial: ' + serial
			if '<<verification>>' in run.text: run.text = 'The authenticity of this certificate can be verified at\nhttp://db.portal.piic.org.ph/verif/' + serial + '/'
	document.save('media/'+serial+'.docx')
	os.system('libreoffice --headless --convert-to pdf media/'+serial+'.docx')
	os.system('mv '+serial+'.pdf static/cert/'+serial+'.pdf')
	os.system('rm media/'+serial+'.docx')
	Message.objects.create(participant=p,category=serial,medium='cert')
	url = static('cert/'+serial+'.pdf')
	return HttpResponseRedirect(url)

def verification(request, serial):
	try:
		m = Message.objects.get(category=serial)
		return render(request, 'plotter/verif.html', {'serial' : serial, 'message' : m})
	except Message.DoesNotExist:
		return render(request, 'plotter/verif.html', {'serial' : serial, 'missing' : True})

@login_required
def master(request):
	cursor = connection.cursor()
	cursor.execute('SELECT DISTINCT(plotter_module.ID) AS ID,topic FROM plotter_module,plotter_training WHERE plotter_training.module_id=plotter_module.ID ORDER BY date,version,topic')
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	if request.user.username == 'dost':
		return render(request, 'plotter/master.html', {'modules' : results, 'restricted' : True})
	else:
		return render(request, 'plotter/master.html', {'modules' : results})

@login_required
def modlist(request, mod_id):
	cursor = connection.cursor()
	if request.user.username == 'dost':
		cursor.execute('SELECT plotter_institution.ID AS instn_id,plotter_institution.abbrev,plotter_module.ID AS mod_id,plotter_training.ID AS training_id,plotter_module.topic,plotter_participant.ID AS ppant_id,sname,fname,designation,graddate,availability,employment,plotter_participant.modified FROM plotter_institution,plotter_module,plotter_participant,plotter_training,plotter_training_trainee WHERE plotter_participant.instn_id=plotter_institution.ID AND plotter_training_trainee.training_id=plotter_training.ID AND plotter_training_trainee.participant_id=plotter_participant.ID AND plotter_training.module_id=plotter_module.ID ORDER BY plotter_institution.abbrev,plotter_participant.designation,plotter_participant.graddate,plotter_participant.sname,plotter_participant.fname,plotter_training.date,plotter_module.version,plotter_module.topic')
	else:
		cursor.execute('SELECT plotter_institution.ID AS instn_id,plotter_institution.abbrev,plotter_module.ID AS mod_id,plotter_training.ID AS training_id,plotter_module.topic,plotter_participant.ID AS ppant_id,sname,fname,designation,plotter_participant.contactn,plotter_participant.email,graddate,availability,employment,workdetails,plotter_participant.modified FROM plotter_institution,plotter_module,plotter_participant,plotter_training,plotter_training_trainee WHERE plotter_participant.instn_id=plotter_institution.ID AND plotter_training_trainee.training_id=plotter_training.ID AND plotter_training_trainee.participant_id=plotter_participant.ID AND plotter_training.module_id=plotter_module.ID ORDER BY plotter_institution.abbrev,plotter_participant.designation,plotter_participant.graddate,plotter_participant.sname,plotter_participant.fname,plotter_training.date,plotter_module.version,plotter_module.topic')
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	return JsonResponse(results, safe=False)

@login_required
def participant(request, ppant_id):
	cursor = connection.cursor()
	cursor.execute('SELECT plotter_participant.*,plotter_module.topic,plotter_training.location,plotter_training.date,plotter_institution.ID AS instn_id,plotter_module.ID AS mod_id,plotter_training.ID AS training_id,plotter_institution.abbrev FROM plotter_participant,plotter_module,plotter_training,plotter_training_trainee,plotter_institution WHERE plotter_participant.ID=%s AND plotter_training.module_id=plotter_module.ID AND plotter_training_trainee.participant_id=plotter_participant.ID AND plotter_training_trainee.training_id=plotter_training.ID AND plotter_participant.instn_id=plotter_institution.ID', [ppant_id])
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	if request.user.username == 'dost':
		return render(request, 'plotter/participant.html', {'results' : results, 'restricted' : True})
	else:
		return render(request, 'plotter/participant.html', {'results' : results})

@login_required
def update(request, ppant_id, availability, employment, workdetails, remarks):
	if request.user.username == 'dost':
		return HttpResponse("This account has insufficient privileges.")
	else:
		x = Participant.objects.get(pk=ppant_id)
		if availability == 'true':
			x.availability = True
		else:
			x.availability = False
		if employment == 'true':
			x.employment = True
		else:
			x.employment = False
		x.workdetails = workdetails
		x.remarks = remarks
		x.save()
		return HttpResponse()

@login_required
def participant_grades(request, ppant_id, training_id):
	cursor = connection.cursor()
	cursor.execute('SELECT plotter_activity.* FROM plotter_activity WHERE participant_id=%s AND training_id=%s', [ppant_id, training_id])
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	return JsonResponse(results, safe=False)

@login_required
def participant_home(request):
	cursor = connection.cursor()
	cursor.execute('SELECT DISTINCT(plotter_participant.instn_id),plotter_institution.abbrev,plotter_institution.fullname FROM plotter_participant,plotter_institution WHERE plotter_participant.instn_id=plotter_institution.ID AND plotter_participant.instructor=0 ORDER BY CASE WHEN plotter_participant.instn_id IS NULL THEN 1 ELSE 0 END, plotter_institution.abbrev')
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	if request.user.username == 'dost':
		return render(request, 'plotter/participant_list.html', {'instns' : results, 'restricted' : True})
	else:
		return render(request, 'plotter/participant_list.html', {'instns' : results})

@login_required
def participant_list(request, instn_id):
	cursor = connection.cursor()
	if request.user.username == 'dost':
		if instn_id != 'None':
			cursor.execute('SELECT plotter_module.ID AS mod_id, plotter_module.topic,plotter_participant.ID AS ppant_id,plotter_participant.sname,plotter_participant.fname,plotter_participant.designation,plotter_participant.graddate,plotter_participant.availability,plotter_participant.employment,plotter_participant.modified FROM plotter_institution,plotter_module,plotter_participant,plotter_training,plotter_training_trainee WHERE plotter_participant.instn_id=plotter_institution.ID AND plotter_training_trainee.training_id=plotter_training.ID AND plotter_training_trainee.participant_id=plotter_participant.ID AND plotter_training.module_id=plotter_module.ID AND plotter_participant.instn_id=%s ORDER BY graddate,designation,sname,fname,topic', [instn_id])
		else:
			cursor.execute('SELECT plotter_module.ID AS mod_id, plotter_module.topic,plotter_participant.ID AS ppant_id,plotter_participant.sname,plotter_participant.fname,plotter_participant.designation,plotter_participant.availability,plotter_participant.employment FROM plotter_institution,plotter_module,plotter_participant,plotter_training,plotter_training_trainee WHERE plotter_participant.instn_id=plotter_institution.ID AND plotter_training_trainee.training_id=plotter_training.ID AND plotter_training_trainee.participant_id=plotter_participant.ID AND plotter_training.module_id=plotter_module.ID AND plotter_participant.instn_id IS NULL ORDER BY graddate,designation,sname,fname,topic')
	else:
		if instn_id != 'None':
			cursor.execute('SELECT plotter_module.ID AS mod_id, plotter_module.topic,plotter_participant.ID AS ppant_id,plotter_participant.sname,plotter_participant.fname,plotter_participant.designation,plotter_participant.graddate,plotter_participant.contactn,plotter_participant.email,plotter_participant.availability,plotter_participant.employment,plotter_participant.modified FROM plotter_institution,plotter_module,plotter_participant,plotter_training,plotter_training_trainee WHERE plotter_participant.instn_id=plotter_institution.ID AND plotter_training_trainee.training_id=plotter_training.ID AND plotter_training_trainee.participant_id=plotter_participant.ID AND plotter_training.module_id=plotter_module.ID AND plotter_participant.instn_id=%s ORDER BY graddate,designation,sname,fname,topic', [instn_id])
		else:
			cursor.execute('SELECT plotter_module.ID AS mod_id, plotter_module.topic,plotter_participant.ID AS ppant_id,plotter_participant.sname,plotter_participant.fname,plotter_participant.designation,plotter_participant.contactn,plotter_participant.email,plotter_participant.availability,plotter_participant.employment FROM plotter_institution,plotter_module,plotter_participant,plotter_training,plotter_training_trainee WHERE plotter_participant.instn_id=plotter_institution.ID AND plotter_training_trainee.training_id=plotter_training.ID AND plotter_training_trainee.participant_id=plotter_participant.ID AND plotter_training.module_id=plotter_module.ID AND plotter_participant.instn_id IS NULL ORDER BY graddate,designation,sname,fname,topic')
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	return JsonResponse(results, safe=False)

@login_required
def module(request, mod_id):
	cursor = connection.cursor()
	cursor.execute('SELECT plotter_module.*,plotter_institution.ID AS instn_id,plotter_institution.abbrev FROM plotter_institution,plotter_institution_module,plotter_module WHERE plotter_institution_module.institution_id=plotter_institution.ID AND plotter_institution_module.module_id=plotter_module.ID AND plotter_module.ID=%s', [mod_id])
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	return render(request, 'plotter/module.html', {'results' :results})

@login_required
def module_related(request, mod_id):
	cursor = connection.cursor()
	cursor.execute('SELECT DISTINCT(plotter_institution.abbrev),plotter_training.ID AS training_id,plotter_training.date,plotter_training.year,plotter_training.location,plotter_institution.ID as instn_id FROM plotter_training,plotter_training_trainee,plotter_participant,plotter_institution WHERE plotter_training_trainee.participant_id=plotter_participant.ID AND plotter_training_trainee.training_id=plotter_training.ID AND plotter_participant.instn_id=plotter_institution.ID AND plotter_training.module_id=%s ORDER BY plotter_training.date', [mod_id])
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	return JsonResponse(results, safe=False)

@login_required
def institution(request, instn_id):
	cursor = connection.cursor()
	cursor.execute('SELECT plotter_institution.*,plotter_module.ID AS mod_id,plotter_module.topic,plotter_module.version FROM plotter_institution,plotter_institution_module,plotter_module WHERE plotter_institution_module.institution_id=plotter_institution.ID AND plotter_institution_module.module_id=plotter_module.ID AND plotter_institution.ID=%s ORDER BY plotter_module.topic,plotter_module.version', [instn_id])
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	if request.user.username == 'dost':
		return render(request, 'plotter/institution.html', {'results' : results, 'restricted' : True})
	else:
		return render(request, 'plotter/institution.html', {'results' : results})

@login_required
def instn_related(request, instn_id):
	cursor = connection.cursor()
	if request.user.username == 'dost':
		cursor.execute('SELECT plotter_training.ID AS training_id,plotter_participant.ID AS ppant_id,plotter_module.topic,plotter_training.date,plotter_participant.sname,plotter_participant.fname,plotter_participant.designation FROM plotter_institution,plotter_module,plotter_participant,plotter_training,plotter_training_trainee WHERE plotter_institution.ID=%s AND plotter_participant.instn_id=plotter_institution.ID AND plotter_training_trainee.training_id=plotter_training.ID AND plotter_training_trainee.participant_id=plotter_participant.ID AND plotter_training.module_id=plotter_module.ID ORDER BY plotter_participant.graddate,plotter_participant.sname,plotter_participant.fname,plotter_module.topic', [instn_id])
	else:
		cursor.execute('SELECT plotter_training.ID AS training_id,plotter_participant.ID AS ppant_id,plotter_module.topic,plotter_training.date,plotter_participant.sname,plotter_participant.fname,plotter_participant.designation,plotter_participant.contactn,plotter_participant.email FROM plotter_institution,plotter_module,plotter_participant,plotter_training,plotter_training_trainee WHERE plotter_institution.ID=%s AND plotter_participant.instn_id=plotter_institution.ID AND plotter_training_trainee.training_id=plotter_training.ID AND plotter_training_trainee.participant_id=plotter_participant.ID AND plotter_training.module_id=plotter_module.ID ORDER BY plotter_participant.graddate,plotter_participant.sname,plotter_participant.fname,plotter_module.topic', [instn_id])
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	return JsonResponse(results, safe=False)

@login_required
def training(request, training_id):
	cursor = connection.cursor()
	cursor.execute('SELECT plotter_training.*,plotter_module.ID AS mod_id,plotter_module.topic,plotter_participant.sname,plotter_participant.fname,plotter_participant.ID AS ppant_id FROM plotter_training,plotter_module,plotter_participant,plotter_training_instructor WHERE plotter_training_instructor.participant_id=plotter_participant.ID AND plotter_training_instructor.training_id=plotter_training.ID AND plotter_training.module_id=plotter_module.ID AND plotter_training.ID=%s', [training_id])
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	if request.user.username == 'dost':
		return render(request, 'plotter/training.html', {'results' : results, 'restricted' : True})
	else:
		return render(request, 'plotter/training.html', {'results' : results})

@login_required
def training_related(request, training_id):
	cursor = connection.cursor()
	if request.user.username == 'dost':
		cursor.execute('SELECT plotter_participant.sname,plotter_participant.fname,plotter_participant.designation,plotter_training_trainee.participant_id AS ppant_id,plotter_participant.instn_id AS instn_id,plotter_institution.abbrev FROM plotter_participant,plotter_institution,plotter_training,plotter_training_trainee WHERE plotter_participant.instn_id=plotter_institution.ID AND plotter_training_trainee.participant_id=plotter_participant.ID AND plotter_training_trainee.training_id=plotter_training.ID AND plotter_training.ID=%s ORDER BY plotter_institution.abbrev,plotter_participant.designation,plotter_participant.sname,plotter_participant.fname', [training_id])
	else:
		cursor.execute('SELECT plotter_participant.*,plotter_training_trainee.participant_id AS ppant_id,plotter_participant.instn_id AS instn_id,plotter_institution.abbrev FROM plotter_participant,plotter_institution,plotter_training,plotter_training_trainee WHERE plotter_participant.instn_id=plotter_institution.ID AND plotter_training_trainee.participant_id=plotter_participant.ID AND plotter_training_trainee.training_id=plotter_training.ID AND plotter_training.ID=%s ORDER BY plotter_institution.abbrev,plotter_participant.designation,plotter_participant.sname,plotter_participant.fname', [training_id])
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	return JsonResponse(results, safe=False)

@login_required
def training_home(request):
	cursor = connection.cursor()
	cursor.execute('SELECT DISTINCT(plotter_module.ID) as mod_id,plotter_module.fullname,plotter_module.topic,plotter_module.version FROM plotter_module,plotter_training WHERE plotter_training.module_id=plotter_module.ID ORDER BY plotter_module.topic,plotter_module.version')
	results = []
	col_names = [name[0] for name in cursor.description]
	for row in cursor.fetchall():
		rowset = []
		for col in zip(col_names, row):
			rowset.append(col)
		results.append(dict(rowset))
	return render(request, 'plotter/training_list.html', {'mods' : results})
