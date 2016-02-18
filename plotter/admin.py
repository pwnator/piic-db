from django.contrib import admin
from plotter.models import *
from django.forms import TextInput, Textarea
from django.db import models

class ModuleInline(admin.TabularInline):
	model = Institution.module.through

class ParticipantInline(admin.TabularInline):
	model = Participant
	fk_name = 'instn'
	ordering = ['sname','fname']
	exclude = ('address','city','province','instructor','linkedin','resume','assignedstaff')
	formfield_overrides = {
		models.CharField: {'widget': TextInput(attrs={'size':'10'})},
		models.TextField: {'widget': TextInput(attrs={'rows':4,'cols':40})},
	}

class ActivityInline(admin.TabularInline):
	model = Activity
	exclude = ('total',)

class InstructorInline(admin.TabularInline):
	model = Training.instructor.through
	maxnum = 2
	extra = 0

class TraineeInline(admin.TabularInline):
	model = Training.trainee.through
	max_num = 3
	extra = 3

class TrainingInline(admin.TabularInline):
	model = Training.trainee.through

class ModuleAdmin(admin.ModelAdmin):
	inlines = [ModuleInline]
	ordering = ['version', 'topic']
	formfield_overrides = {
		models.CharField: {'widget': TextInput(attrs={'size':'20'})},
		models.TextField: {'widget': TextInput(attrs={'rows':4,'cols':40})},
	}

class InstitutionAdmin(admin.ModelAdmin):
	inlines = [ParticipantInline]
	ordering = ['abbrev']
	formfield_overrides = {
		models.CharField: {'widget': TextInput(attrs={'size':'20'})},
		models.TextField: {'widget': TextInput(attrs={'rows':4,'cols':40})},
	}

class ParticipantAdmin(admin.ModelAdmin):
	fieldsets = [
		('Personal information', {'fields': [('sname','fname'),'instn','email','contactn',('designation','graddate'),('address','city','province'),'instructor',('availability','employment'),'workdetails','remarks','modified']}),
	]
	readonly_fields = ('modified',)
	inlines = [TrainingInline]
	list_display = ('__str__','instn')
	search_fields = ['sname','fname','instn__abbrev','instn__fullname']
	ordering = ['instn','sname']

class TrainingAdmin(admin.ModelAdmin):
	fieldsets = [
		('Information', {'fields': [('module','location'),('date','year')]}),
	]
	inlines = [InstructorInline, TraineeInline]
	list_display = ('__str__','date')
	search_fields = ['module__topic','location','year']
	ordering = ['location','year','module']

class ActivityAdmin(admin.ModelAdmin):
	search_fields = ['training__location','training__module__topic','training__year','participant__sname','participant__fname']

class MessageAdmin(admin.ModelAdmin):
	fieldsets = [
		('Information', {'fields': [('participant','timestamp'),('category')]}),
	]
	readonly_fields = ['timestamp']
	list_display = ('__str__','timestamp')

admin.site.register(Module, ModuleAdmin)
admin.site.register(Institution, InstitutionAdmin)
admin.site.register(Training, TrainingAdmin)
admin.site.register(Participant, ParticipantAdmin)
admin.site.register(Activity, ActivityAdmin)
admin.site.register(Evaluation)
admin.site.register(Message, MessageAdmin)
