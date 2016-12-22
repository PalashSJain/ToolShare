import re

from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from pip._vendor.requests.utils import is_valid_cidr

from tool_share.models import *
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext as _
from django.forms.models import ModelForm
from datetime import date, timedelta
from django.contrib import messages
import os
from django.conf import settings

# If you don't do this you cannot use Bootstrap CSS
class LoginForm(AuthenticationForm):
	username = forms.CharField(label="Email", max_length=255)
	password = forms.CharField(label="Password", max_length=30, min_length=6, widget=forms.PasswordInput())

	class Meta:
		model = CustomUser

	def clean(self):
		username = self.cleaned_data.get('username').lower()
		password = self.cleaned_data.get('password')

		if username and password:
			self.user_cache = authenticate(username=username,
										   password=password)
			if self.user_cache is None:
				raise forms.ValidationError(
					self.error_messages['invalid_login'],
					code='invalid_login',
					params={'username': self.username_field.verbose_name},
				)
			else:
				self.confirm_login_allowed(self.user_cache)

		return self.cleaned_data


class CustomUserCreationForm(UserCreationForm):
	class Meta:
		model = CustomUser
		fields = ("username", "first_name", "last_name", "address", "zip_code", "phone_number")

	def save(self, commit=True):
		user = super(CustomUserCreationForm, self).save(commit=False)
		# copy the submitted cleaned form-data to the user's properties
		user.set_password(self.cleaned_data["password1"])
		user.username = self.cleaned_data["username"]
		user.first_name = self.cleaned_data["first_name"]
		user.last_name = self.cleaned_data["last_name"]
		user.address = self.cleaned_data["address"]
		user.zip_code = self.cleaned_data["zip_code"]
		user.phone_number = self.cleaned_data["phone_number"]
		if commit:
			zone = ShareZone.register(user.zip_code)
			# save the user properties to the db fields
			user.save()
#             Notification.make_note(Notification.USER_JOIN,zone,user)
		return user


def reuse_clean_picture_path(formobj):
	self=formobj
	haveNewFileToUpload = self.files

	if haveNewFileToUpload:
		attempted_file = self.cleaned_data['picture_path']
		attempted_extension = attempted_file.name.split('.')[-1]
		attempted_file_size = attempted_file._size
		allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']
		size_limit = 5242880  # 5MB
		if attempted_extension not in allowed_extensions:
			msg = "File must be an image."
			self.add_error('picture_path', forms.ValidationError(_(msg)))
		else:
			if attempted_file_size > size_limit:
				msg = "Image must be less than 5MB."
				self.add_error('picture_path', forms.ValidationError(_(msg)))
			else:
				return attempted_file  # persist this return value as the cleaned_data.picture_path value
	else:
		existingFileToKeep = self.cleaned_data['picture_path']
		if existingFileToKeep:
			return existingFileToKeep
		# if form was initialized with instance=None, then will set instance.pp=cleaned_data.pp?
		# if form was initialized with instance=ToolItem, then instance.pp=ToolItem.pp not cleaned_data.pp?

def reuse_save_with_file(form,inst,commit):
	self=form

	# copy the submitted cleaned form-data to the instance's properties
	initialFile = self.initial['picture_path']
	finalFile = self.cleaned_data['picture_path']
	inst.picture_path = finalFile

	if commit:
		initialFileName = initialFile.name if initialFile else ''
		finalFileName = finalFile.name if finalFile else ''

		if initialFileName != finalFileName:
			if initialFileName == '':
				if inst.pk is None:
					inst.picture_path = None
					inst.save()  # generate a pk to use as the filePath
					inst.picture_path = finalFile
			else:
				initialPath = settings.MEDIA_ROOT + '/' + initialFileName
				os.remove(initialPath)  # delete previously uploaded image

		inst.save()

	return inst

class CustomUserEditForm(forms.ModelForm):
	class Meta:
		model = CustomUser
		fields = ("picture_path", "username", "first_name", "last_name", "address", "zip_code", "phone_number")

	def clean_picture_path(self): #this executes from form.is_valid() before form's clean
		return reuse_clean_picture_path(self)

	def clean(self):
		cleaned_data = super(CustomUserEditForm, self).clean()
		user = self.instance
		initialzip = user.zip_code
		finalzip = cleaned_data.get("zip_code")

		if initialzip != finalzip:
			[success,leavezoneerrors] = user.leavezone()
			if not success:
				self.add_error('zip_code', forms.ValidationError(_(leavezoneerrors)))
			else:
				user.joinzone(finalzip)

	def save(self, commit=True):
		# get the instance from the form
		user = self.instance
		return reuse_save_with_file(self, user, commit)

class AddToolForm(forms.ModelForm):
	def __init__(self, *args, **kwargs):
		super(AddToolForm, self).__init__(*args, **kwargs)
		try:
			get_object_or_404(Sheds, zip_code=self.instance.ownedBy.zip_code)
		except:
			self.fields['pickupDropLoc'].choices = [(ToolItem.HOME, "Home")]

	class Meta:
		model = ToolItem
		# the order of this list dictates the foreach order in the template
		fields = ['title', 'picture_path', 'description','special_instructions','pickupDropLoc']

	def clean_picture_path(self): #this executes from form.is_valid() before form's clean
		return reuse_clean_picture_path(self)

	def save(self, commit=True):

		# get the instance from the form
		tool = self.instance
		if tool is None:
			tool = super(AddToolForm, self).save(commit=False)

		return reuse_save_with_file(self,tool,commit)

class VerifyToolForm(forms.ModelForm):
	class Meta:
		model = ToolItem
		fields = ['condition',]

class CreateReservationForm(forms.ModelForm):
	#override model field's default form field with a non-default form field
	start_date = forms.DateField(widget=forms.SelectDateWidget,initial=date.today())
	end_date = forms.DateField(widget=forms.SelectDateWidget,initial=date.today()+timedelta(1))
	# models.DateField has default forms.DateField has default widget=forms.DateInput which is <input type='text'>
	# widget=forms.SelectDateWidget is 3 <select>s: for month, day, and year


	def clean(self):
		cleaned_data = super(CreateReservationForm, self).clean()
		start_date = cleaned_data.get("start_date")
		end_date = cleaned_data.get("end_date")
		resv = self.instance
		resv.start_date = start_date
		resv.end_date = end_date

		if start_date and start_date < date.today():
			msg = "Start date cannot be before today."
			self.add_error('start_date', forms.ValidationError(_(msg) ))

		if start_date and end_date and end_date < start_date:
			msg = "End date must be after start date."
			self.add_error('end_date', forms.ValidationError(_(msg) ))

		if start_date and end_date and end_date > start_date + timedelta(days=14):
			msg = "Each request can only be a maximum of 2 weeks."
			self.add_error('end_date', forms.ValidationError(_(msg)))

		if start_date and end_date and resv.get_preventing_conflicts().count() > 0:
			msg = "This time period is not available."
			self.add_error(None, forms.ValidationError(_(msg) ))


	class Meta:
		model = Reservation

		#the order of this list dictates the foreach order in the template
		fields = ('start_date','end_date','message_from_borrower',)

class ReservationApprovalForm(forms.ModelForm):
	APPROVAL_CHOICES = ((Reservation.APPROVED, 'Approve'), (Reservation.REJECTED, 'Reject'))
	approval = forms.ChoiceField(choices=APPROVAL_CHOICES, widget=forms.RadioSelect,required=True)
	def clean(self):
		cleaned_data = super(ReservationApprovalForm, self).clean()
		resv_type=cleaned_data.get('approval')
		reason=cleaned_data.get('reason_for_rejection')
		if resv_type and int(resv_type)==Reservation.REJECTED and reason=="":
			msg = "When rejecting, a reason is required."
			self.add_error('reason_for_rejection', forms.ValidationError(_(msg) ))

	def save(self, commit=True):
		# get the instance from the form
		resv = self.instance
		if resv is None:
			resv = super(ReservationApprovalForm, self).save(commit=False)

		# copy the submitted cleaned form-data to the instance's properties
		resv.resv_type = int(self.cleaned_data['approval'])
		if commit:
			resv.save()
		return resv

	class Meta:
		model = Reservation

		#the order of this list dictates the order in the template
		fields = ('reason_for_rejection',)


class CreateShedForm(ModelForm):
	class Meta:
		model = Sheds
		fields = ['street_address','city']