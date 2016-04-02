from django.db import models
from django.template.defaultfilters import slugify
from decimal import Decimal

class Module(models.Model):	
	topic = models.CharField(max_length=8)
	fullname = models.CharField(max_length=64)
	version = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('1.00'))
	moddate = models.IntegerField(blank=True, null=True)
	description = models.TextField(blank=True, null=True)
	topics = models.TextField(blank=True, null=True)
	remarks = models.TextField(blank=True, null=True)

	def __str__(self):
		return '%s v%d' % (self.topic, self.version)

class Institution(models.Model):
	abbrev = models.CharField(max_length=16)
	fullname = models.CharField(max_length=64)
	email = models.EmailField(blank=True, null=True)
	fields = models.CharField(max_length=128, blank=True, null=True)
	address = models.CharField(max_length=128, blank=True, null=True)
	city = models.CharField(max_length=32, blank=True, null=True)
	province = models.CharField(max_length=16, blank=True, null=True)
	logo = models.CharField(max_length=32, blank=True, null=True)
	module = models.ManyToManyField(Module, related_name='modules', blank=True)

	def __str__(self):
		return self.abbrev

class Participant(models.Model):
	sname = models.CharField(max_length=32)
	fname = models.CharField(max_length=64)
	mi = models.CharField(max_length=4, blank=True, null=True)
	email = models.EmailField(blank=True, null=True)
	contactn = models.IntegerField(blank=True, null=True)
	instn = models.ForeignKey(Institution, blank=True, null=True)
	designation = models.CharField(max_length=64, blank=True, null=True)
	address = models.CharField(max_length=128, blank=True, null=True)
	city = models.CharField(max_length=32, blank=True, null=True)
	province = models.CharField(max_length=16, blank=True, null=True)
	graddate = models.IntegerField(blank=True, null=True)
	instructor = models.BooleanField(default=False)
	linkedin = models.CharField(max_length=255, blank=True, null=True)
	resume = models.CharField(max_length=255, blank=True, null=True)
	availability = models.BooleanField(default=False)
	employment = models.BooleanField(default=False)
	company = models.CharField(max_length=16, blank=True, null=True)
	workdetails = models.TextField(blank=True, null=True)
	remarks = models.TextField(blank=True, null=True)
	modified = models.DateTimeField(auto_now=True)
	
	def __str__(self):
		return '%s, %s' % (self.sname, self.fname)

class Training(models.Model):
	module = models.ForeignKey(Module)
	location = models.CharField(max_length=16)
	date = models.IntegerField(blank=True, null=True)
	year = models.IntegerField(blank=True, null=True)
	instructor = models.ManyToManyField(Participant, related_name='instructors')
	trainee = models.ManyToManyField(Participant, related_name='trainees')
	staff = models.ManyToManyField(Participant, related_name='staff')

	def __str__(self):
		return '%s - %s Y%d' % (self.module, self.location, self.year)

class Activity(models.Model):
	training = models.ForeignKey(Training)
	participant = models.ForeignKey(Participant, blank=True, null=True)
	category = models.CharField(max_length=16)
	title = models.CharField(max_length=64, blank=True, null=True)
	score = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
	total = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)

	class Meta:
		verbose_name_plural = "activities"

	def __str__(self):
		return '%s - %s (%s)' % (self.training, self.participant, self.category)

class Evaluation(models.Model):
	activity = models.ForeignKey(Activity)
	question = models.CharField(max_length=64, blank=True, null=True)
	answer = models.TextField(blank=True, null=True)

	def __str__(self):
		return '%s - %s' % (self.activity, self.question)

class Message(models.Model):
	participant = models.ForeignKey(Participant)
	medium = models.CharField(max_length=4, blank=True, null=True)
	category = models.CharField(max_length=64, blank=True, null=True)
	timestamp = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return '%s - %s' % (self.category, self.participant)
