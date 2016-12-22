from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from datetime import datetime, date
from time import gmtime, strftime
from django.template.defaulttags import register
from django.db.models import Q

# the templates use this to lookup the text for each enum int
@register.filter
def get_enum(dictionary, key):
	#attributes of dicts are accessed via dict['myattrib'] NOT dict.myattrib
	#elements of a list are accessed via list.elementIndex or list[elementIndex]
	return dictionary[key][1]

	# Create your models here.
class CustomUserManager(BaseUserManager):
	def create_user(self, username, password=None):
		if not username:
			raise ValueError('Users must have an email address')

		user = self.model(
			username=self.normalize_email(username),
		)

		user.set_password(password)
		user.save(using=self._db)
		return user

	def create_superuser(self, username, password, **kwargs):
		user = self.model(
			username=username,
			is_staff=True,
			is_superuser=True,
			is_active=True,
			is_admin=True,
			zip_code=00000,
			**kwargs
		)
		user.set_password(password)
		user.save(using=self._db)
		return user

def concatMediaPathUser(instance,filename):
	return 'users/userId_' + \
		   str(instance.id) + \
		   '.' + filename.split('.')[-1]

class CustomUser(AbstractBaseUser, PermissionsMixin):
	SUPERUSER = 1

	SHED_NEWS = 0
	REMINDERS = 1
	NOTIFICATION_PREFERENCES = (
		(SHED_NEWS, "Member, Tool, Admin Join/Leave Shed"),
		(REMINDERS, "Reservation Reminder"),
	)

	username = models.EmailField(verbose_name='email address', max_length=255, unique=True, null=False) #unique is case-sensitive
	first_name = models.CharField(verbose_name='first name', max_length=30, unique=False, null=False)
	last_name = models.CharField(verbose_name='last name', max_length=30, unique=False, null=True)

	picture_path = models.FileField(upload_to=concatMediaPathUser, null=True, blank=True)  # a subdirectory of MEDIA_ROOT to use
	zip_code_validator = RegexValidator(regex='^[0-9]{5}(?:-[0-9]{4})?$', message=u'Zip Code is invalid.')
	zip_code = models.IntegerField(verbose_name='zip code', blank=False, validators=[zip_code_validator])
	phone_number_validator = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
	phone_number = models.CharField(verbose_name='phone number', blank=False,null=False, unique=False, max_length=15, validators=[phone_number_validator])
	is_active = models.BooleanField(default=True)
	is_admin = models.BooleanField(default=False)
	address = models.CharField(verbose_name='address', max_length=255, null=True, blank=True)
	is_coordinator = models.BooleanField(default=False)
	preferences = models.IntegerField(choices=NOTIFICATION_PREFERENCES, default=SHED_NEWS)

	objects = CustomUserManager()

	last_notification_visit = models.DateTimeField(default=datetime.now())

	USERNAME_FIELD = 'username'
	REQUIRED_FIELDS = []

	def is_last_member(self):
		members=CustomUser.objects.filter(zip_code=self.zip_code)
		return members.count()==1

	def is_last_coordinator(self):
		members=CustomUser.objects.filter(zip_code=self.zip_code)
		coordinators=members.filter(is_coordinator=True)
		return coordinators.count()==1 and coordinators[0]==self

	def promote_to_coordinator(self):
		# if a shed has not been created, cannot promote to coordinator
		sheds=Sheds.objects.filter(zip_code=self.zip_code)
		if sheds.count() > 0:
			self.is_coordinator = True
			self.save()
			return [True, ""]
		return [False, "Cannot promote to coordinator in a zone without a shed. "]

	def demote_from_coordinator(self):
		# if a shed has been created, cannot be the last coordinator
		sheds=Sheds.objects.filter(zip_code=self.zip_code)
		if sheds.count() > 0 and not self.is_last_coordinator():
			self.is_coordinator = False
			self.save()
			return [True, ""]
		return [False, "Cannot demote the last coordinator of a zone with a shed. "]

	def is_lending_pickedup_tools(self):
		pickedup=ToolItem.objects.filter(ownedBy=self,possession=ToolItem.PICKED_UP)
		return pickedup.count() > 0

	def is_lending_unverified_tools(self):
		unverified = ToolItem.objects.filter(ownedBy=self,possession=ToolItem.RETURNED)
		return unverified.count() > 0

	def is_borrowing_pickedup_tools(self):
		pickedup = ToolItem.objects.filter(possession=ToolItem.PICKED_UP,
											 reservation__borrower=self,
											 reservation__resv_type=Reservation.APPROVED,
											 reservation__start_date__lte=date.today(),
											 reservation__end_date__gte=date.today()
											 )
		return pickedup.count() > 0

	def get_myfuture_borrowing_resvs(self):
		return Reservation.objects.filter(borrower=self,end_date__gte=date.today())

	def get_leave_zone_msgs(self):
		msgs=""
		if not self.is_last_member():
			if self.is_lending_pickedup_tools():
				msgs += "You cannot move while your tools are being lent. "
			if self.is_lending_unverified_tools():
				msgs += "You cannot move while you have unverified tools. "
			if self.is_borrowing_pickedup_tools():
				msgs += "You must return your borrowed tools before moving. "
			if self.is_last_coordinator():
				msgs += "You must promote another user to coordinator before moving. "
		return msgs

	def leavezone(self):
		#return format: [LeaveSuccessTrueFalse, StringErrorMessages]

		# see if there are any leave shed conflicts
		errormsgs = self.get_leave_zone_msgs()
		if errormsgs != "":
			return [False,errormsgs]

		if self.is_last_member():
			# delete zone and shed
			sheds=Sheds.objects.filter(zip_code=self.zip_code)
			for shed in sheds:
				shed.delete()
			zone=ShareZone.objects.filter(zip_code=self.zip_code).first()
			zone.delete()

		else:
			# cancel all future borrowing resvs
			Reservation.cancel_and_reject_borrowing_conflicts(self.get_myfuture_borrowing_resvs())
			# cancel all future lending resv
			mytools = ToolItem.objects.filter(ownedBy=self)
			for tool in mytools:
				Reservation.cancel_and_reject_lending_conflicts(Reservation.get_same_tool_and_future_conflicts(tool))

		# remove zip code
		self.zip_code = -1
		self.save()
		return [True,""]

	def joinzone(self, newzip):
		ShareZone.register(newzip)
		self.zip_code=newzip
		self.save()

	def get_join_zone_msgs(self):
		myshedtools=ToolItem.objects.filter(ownedBy=self,pickupDropLoc=ToolItem.SHED)
		newshed=Sheds.objects.filter(zip_code=self.zip_code).first()
		if myshedtools.count() > 0 and newshed is None:
			return "You have tools not shared from home. Create a shed now! "
		return ""

	def get_full_name(self):
		# The user is identified by their email address
		return self.username

	def get_short_name(self):
		# The user is identified by their email address
		return self.username

	def __str__(self):  # __unicode__ on Python 2
		return self.first_name + " " + self.last_name

	def has_perm(self, perm, obj=None):
		return True

	def has_module_perms(self, app_label):
		return True

	@property
	def is_staff(self):
		return self.is_admin

def concatMediaPath(instance,filename):
	return 'tools/userId_' + \
		   str(instance.ownedBy.id) + \
		   '/toolId_' + \
		   str(instance.pk) + \
		   '.' + filename.split('.')[-1]


class ToolItem(models.Model):

	GOOD = 0
	POOR = 1
	BROKEN = 2
	MISSING = 3
	CONDITION_CHOICES = (
		(GOOD, "Good"),
		(POOR, "Poor"),
		(BROKEN, "Broken"),
		(MISSING, "Missing"),
	)

	DEACTIVATED = 0
	ACTIVATED = 1
	ACTIVATION_CHOICES = (
		(DEACTIVATED, "Deactivated"),
		(ACTIVATED, "Activated"),
	)

	PICKED_UP = 0
	RETURNED = 1
	VERIFIED_RETURNED = 2
	POSSESSION_CHOICES = (
		(PICKED_UP, "Picked up"),
		(RETURNED, "Returned"),
		(VERIFIED_RETURNED, "Verified")
	)

	SHED = 0
	HOME = 1
	SHAREFROM_CHOICES = (
		(SHED, "Shed"),
		(HOME, "Home"),
	)

	# tool details
	ownedBy = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
	picture_path = models.FileField(upload_to=concatMediaPath, null=True, blank=True)  # a subdirectory of MEDIA_ROOT to use
	title = models.CharField(max_length=100,unique=True)
	description = models.TextField(max_length=255, blank=True)
	special_instructions = models.TextField(max_length=255, blank=True)
	pickupDropLoc = models.IntegerField(choices=SHAREFROM_CHOICES, default=SHED)
	activation = models.IntegerField(choices=ACTIVATION_CHOICES, default=ACTIVATED)
	condition = models.IntegerField(choices=CONDITION_CHOICES, default=GOOD)
	possession = models.IntegerField(choices=POSSESSION_CHOICES, default=VERIFIED_RETURNED)

	# class Meta:
	# 	unique_together = ('ownedBy', 'title')

	def clean(self): #this executes from form.is_valid(), after fields' cleans and after form's clean
		return

	def get_borrowedTo(self):
		if self.possession != self.VERIFIED_RETURNED:
			query = Q(tool=self) & Q(start_date__lte=date.today()) & Q(end_date__gte=date.today())
			resv = Reservation.objects.filter(query).first()
			if resv is not None:
				return resv.borrower
		return None

	def is_available(self):
		reservations = Reservation.objects.filter(tool=self)
		for i in range(len(reservations)):
			if reservations[i].start_date <= date.today() and reservations[i].end_date >= date.today():
				return False
		return True

	def get_tool_pickup_address(self):
		if self.pickupDropLoc == ToolItem.HOME:
			return self.ownedBy.address
		else:
			shed = Sheds.objects.get(zip_code=self.ownedBy.zip_code)
			return shed.street_address

	def __str__(self):
		return self.title

	def get_unavailabilities(self, viewer):
		blockouts = Q(resv_type=Reservation.BLOCKOUT)
		my_previous_request = Q(resv_type=Reservation.REQUESTED) & Q(borrower=viewer)
		approvals = Q(resv_type=Reservation.APPROVED)
		conflicting_type = my_previous_request | approvals | blockouts
		conflicts = Reservation.get_same_tool_and_future_conflicts(self).filter(conflicting_type).order_by('start_date')
		return conflicts

	def get_remove_tool_msgs(self):
		msgs=""
		if self.possession == ToolItem.PICKED_UP:
			msgs += "You cannot delete while this tool is being lent. "
		if self.possession == ToolItem.RETURNED:
			msgs += "You cannot delete while this tool is unverified. "
		return msgs

	def removetool(self):
		#return format: [RemoveSuccessTrueFalse, StringErrorMessages]

		# see if there are any remove tool conflicts
		errormsgs = self.get_remove_tool_msgs()
		if errormsgs != "":
			return [False,errormsgs]

		# cancel all past and future reservations
		# resvs=Reservation.objects.filter(tool=self)
		# for resv in resvs:
		# 	resv.delete()

		# Reservation.delete_blockout_conflicts(Reservation.get_same_tool_and_future_conflicts(self))
		# Reservation.cancel_and_reject_lending_conflicts(Reservation.get_same_tool_and_future_conflicts(self))

		# delete tool
		self.delete()
		return [True,""]

class ShareZone(models.Model):
	zip_code = models.IntegerField(unique=True)

	def register(zipcode):
		obj, created = ShareZone.objects.get_or_create(zip_code=zipcode)
		return created

class Sheds(models.Model):
	# toString method
	def __str__(self):
		return 'Shed ' + str(self.zip_code)

	# fields
	zip_code = models.IntegerField(unique=True)
	street_address = models.CharField(max_length=55)
	city = models.CharField(max_length=25)

	def removeshed(self): #????
		# no shed coordinators can exist in a zone without a shed
		# force all tools to be shared from home
		sheds=Sheds.objects.filter(zip_code=self.zip_code)
		if sheds.count() > 0:
			self.is_coordinator = True
			self.save()
			return [True, ""]
		return [False, "Cannot promote to coordinator in a zone without a shed. "]

class Reservation(models.Model):

	BLOCKOUT = 0
	REQUESTED = 1
	APPROVED = 2
	REJECTED = 3
	CANCELLED_BY_LENDER = 4
	CANCELLED_BY_BORROWER = 5
	UNBLOCKED = 6
	RESERVATION_TYPES = (
		(BLOCKOUT, "Owner Blocked Out"),
		(REQUESTED, "Awaiting Borrower's Approval"),
		(APPROVED, "Lender Approved"),
		(REJECTED, "Lender Rejected"),
		(CANCELLED_BY_LENDER, "Cancelled by Lender"),
		(CANCELLED_BY_BORROWER, "Cancelled by Borrower"),
		(UNBLOCKED, "Unblocked by Owner"),
	)

	resv_type = models.IntegerField(choices=RESERVATION_TYPES, default=REQUESTED)
	tool = models.ForeignKey(ToolItem, on_delete=models.CASCADE, null=True)
	borrower = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

	start_date = models.DateField()
	end_date = models.DateField()
	message_from_borrower = models.TextField(max_length=255, null=True, blank=True)
	reason_for_rejection = models.TextField(max_length=255, null=True, blank=True)

	@property
	def has_ended(self):
		if self.end_date <= date.today():
			return True
		return False

	def has_started(self):
		if self.start_date <= date.today():
			return True
		return False

	def get_same_tool_and_future_conflicts(toolitem):
		same_tool = Q(tool=toolitem)
		future_overlap = Q(end_date__gt=date.today())
		conflicts = Reservation.objects.filter(same_tool & future_overlap)
		return conflicts

	def get_same_tool_and_time_conflicts(self):
		same_tool = Q(tool=self.tool)
		start_overlap = Q(start_date__gte=self.start_date) & Q(start_date__lt=self.end_date)
		end_overlap = Q(end_date__gt=self.start_date) & Q(end_date__lte=self.end_date)
		same_time = start_overlap | end_overlap
		conflicts = Reservation.objects.filter(same_tool & same_time)
		return conflicts

	def get_preventing_conflicts(self):
		blockouts = Q(resv_type=Reservation.BLOCKOUT)
		if self.resv_type == Reservation.BLOCKOUT:
			conflicting_type = blockouts
		else:
			my_previous_request = Q(resv_type=Reservation.REQUESTED) & Q(borrower=self.borrower)
			approvals = Q(resv_type=Reservation.APPROVED)
			conflicting_type = my_previous_request | approvals | blockouts
		conflicts = self.get_same_tool_and_time_conflicts().filter(conflicting_type)
		return conflicts

	def update_resv_type(self, new_type):
		self.resv_type = new_type
		self.save_with_note()

	def update_lending_requests(tool_and_time_subset,new_resv_type):
		requests_to_update = Q(resv_type=Reservation.REQUESTED)
		# reject all requests for this subset
		for resv in tool_and_time_subset.filter(requests_to_update):
			resv.reason_for_rejection = "Conflicts with updated availability."
			resv.update_resv_type(new_resv_type)

	def cancel_and_reject_lending_conflicts(tool_and_time_subset):
		approvals_to_cancel = Q(resv_type=Reservation.APPROVED)
		# cancel all reservations for this subset
		for resv in tool_and_time_subset.filter(approvals_to_cancel):
			resv.update_resv_type(resv.CANCELLED_BY_LENDER)
		# reject all requests for this subset
		Reservation.update_lending_requests(tool_and_time_subset,Reservation.REJECTED)

	def delete_blockout_conflicts(tool_and_time_subset):
		blockouts_to_delete = Q(resv_type=Reservation.BLOCKOUT)
		# delete all blockouts for this subset
		for resv in tool_and_time_subset.filter(blockouts_to_delete):
			resv.delete()

	def cancel_and_reject_borrowing_conflicts(tool_and_time_subset):
		approvals_to_cancel = Q(resv_type=Reservation.APPROVED)
		requests_to_cancel = Q(resv_type=Reservation.REQUESTED)
		# cancel all futures for this subset
		for resv in tool_and_time_subset.filter(approvals_to_cancel | requests_to_cancel):
			resv.update_resv_type(resv.CANCELLED_BY_BORROWER)

	def save_with_note(self):
		self.save()
		self.make_resv_note()

	def make_resv_note(self):
		if self.resv_type == self.REQUESTED:
			Notification.make_notification(note_type=Notification.TASK_APPROVE_RESERVATION, display_to=Notification.LENDER,
										   borrower=self.borrower, lender=self.tool.ownedBy, start_date=self.start_date,
										   end_date=self.end_date, tool=self.tool)
		elif self.resv_type == self.APPROVED:
			Notification.make_notification(note_type=Notification.REPORT_APPROVAL, display_to=Notification.BORROWER,
							   borrower=self.borrower, lender=self.tool.ownedBy, start_date=self.start_date,
							   end_date=self.end_date, tool=self.tool)
		elif self.resv_type == self.REJECTED:
			Notification.make_notification(note_type=Notification.REPORT_DISAPPROVAL, display_to=Notification.BORROWER,
							   borrower=self.borrower, lender=self.tool.ownedBy, start_date=self.start_date,
							   end_date=self.end_date, tool=self.tool)
		elif self.resv_type == self.CANCELLED_BY_LENDER:
			Notification.make_notification(note_type=Notification.CANCELLED_BY_LENDER, display_to=Notification.BORROWER,
										   borrower=self.borrower, lender=self.tool.ownedBy, start_date=self.start_date,
										   end_date=self.end_date, tool=self.tool)
		elif self.resv_type == self.CANCELLED_BY_BORROWER:
			Notification.make_notification(note_type=Notification.CANCELLED_BY_BORROWER, display_to=Notification.LENDER,
										   borrower=self.borrower, lender=self.tool.ownedBy, start_date=self.start_date,
										   end_date=self.end_date, tool=self.tool)

class Notification(models.Model):
	COORDINATOR_JOIN = 0
	COORDINATOR_LEFT = 1
	USER_JOIN = 2
	USER_LEFT = 3
	SHED_ADDRESS_CHANGE = 4
	RESERVATION_REMINDER = 5
	TASK_VERIFY_TOOL_RETURNS = 6
	TASK_APPROVE_RESERVATION = 7
	REPORT_APPROVAL = 8
	CANCELLED_BY_BORROWER = 9
	CANCELLED_BY_LENDER = 10
	REPORT_DISAPPROVAL = 11
	NOTIFICATION_TYPES = (
		(COORDINATOR_JOIN, "Coordinator Joined Shed"),  #
		(COORDINATOR_LEFT, "Coordinator Left Shed"),
		(USER_JOIN, "Member Joined Shed"),
		(USER_LEFT, "Member Left Shed"),
		(SHED_ADDRESS_CHANGE, "Shed Street Address Changed"),
		(RESERVATION_REMINDER, "Reservation Reminder"),
		(TASK_VERIFY_TOOL_RETURNS, "Lender Needs to Verify Tool"),
		(TASK_APPROVE_RESERVATION, "Lender Needs to Approve Request"),
		(REPORT_APPROVAL, "Request Approved"),
		(REPORT_DISAPPROVAL, "Request Declined"),
		(CANCELLED_BY_BORROWER, "Cancellation by Borrower"),
		(CANCELLED_BY_LENDER, "Cancellation by Lender"),
	)
	BORROWER = 0
	LENDER = 1
	timestamp = models.DateTimeField()
	type = models.IntegerField(choices=NOTIFICATION_TYPES, default=-1, null=True)
	borrower = models.ForeignKey(CustomUser, related_name="other_user", null=True)
	lender = models.ForeignKey(CustomUser, related_name="main_user")
	tool = models.ForeignKey(ToolItem, null=True)
	display_to = models.ForeignKey(CustomUser, related_name="display_to")
	start_date = models.DateField(null=True)
	end_date = models.DateField(null=True)

	def make_notification(note_type, display_to, borrower, lender, start_date, end_date, tool=None):
		note = Notification()
		note.timestamp = datetime.now()
		note.type = note_type
		note.tool = tool
		note.borrower = borrower
		note.lender = lender
		note.start_date = start_date
		note.end_date = end_date
		if display_to == Notification.BORROWER:
			note.display_to = borrower
		else:
			note.display_to = lender
		note.save()

	def get_relative_URL(self):
		if self.type == self.TASK_VERIFY_TOOL_RETURNS:
			return "/mytools/"
		elif self.type == self.TASK_APPROVE_RESERVATION:
			return "/mylendlist/"
		elif self.type == self.REPORT_APPROVAL:
			return "/myborrowlist/"
		elif self.type == self.CANCELLED_BY_BORROWER:
			return "/mylendlist/"
		elif self.type == self.CANCELLED_BY_LENDER:
			return "/myborrowlist/"
		elif self.type == self.REPORT_DISAPPROVAL:
			return "/myborrowlist/"
		else:
			pass

	def get_message(self):
		if self.type == self.TASK_VERIFY_TOOL_RETURNS:
			return self.get_message_TASK_VERIFY_TOOL_RETURNS()
		elif self.type == self.TASK_APPROVE_RESERVATION:
			return self.get_message_TASK_APPROVE_RESERVATION()
		elif self.type == self.REPORT_APPROVAL:
			return self.get_message_REPORT_APPROVAL()
		elif self.type == self.CANCELLED_BY_BORROWER:
			return self.get_message_CANCELLED_BY_BORROWER()
		elif self.type == self.CANCELLED_BY_LENDER:
			return self.get_message_CANCELLED_BY_LENDER()
		elif self.type == self.REPORT_DISAPPROVAL:
			return self.get_message_REPORT_DISAPPROVAL()
		else:
			pass

	# SOMEUSER returned YOUR TOOL at TIME. Please verify it.
	def get_message_TASK_VERIFY_TOOL_RETURNS(self):
		return self.get_timestamp() +", "+ self.get_tool() + "  was returned. Please verify it's condition."

	# SOMEUSER has requested to borrow YOUR TOOL from THIS to THEN.
	def get_message_TASK_APPROVE_RESERVATION(self):
		return self.get_timestamp() +", "+ self.get_borrower() + " has requested to borrow " + self.get_tool() + " from " + self.get_start_time() + " to " + self.get_end_time() + "."

	# SOMEUSER has approved YOUR request for TOOL from THIS to THEN.
	def get_message_REPORT_APPROVAL(self):
		return self.get_timestamp() +", "+ self.get_lender() + " has approved your request for " + self.get_tool() + " from " + self.get_start_time() + " to " + self.get_end_time()

	# SOMEUSER has declined YOUR request for TOOL from THIS to THEN.
	def get_message_REPORT_DISAPPROVAL(self):
		return self.get_timestamp() +", "+ self.get_lender() + " has declined your request for " + self.get_tool() + " from " + self.get_start_time() + " to " + self.get_end_time()

	#Reservation for TOOL, from THIS to THEN, has been cancelled by SOMEUSER.
	def get_message_CANCELLED_BY_BORROWER(self):
		return self.get_timestamp() +", "+ "Reservation for " + self.get_tool() + ", from " + self.get_start_time() + " to " + self.get_end_time() + ", has been cancelled by " + self.get_borrower()

	# SOMEUSER has cancelled your reservation for TOOL.
	def get_message_CANCELLED_BY_LENDER(self):
		return self.get_timestamp() +", "+ self.get_lender() + " has cancelled your reservation for " + self.get_tool()

	def get_time(self):
		return str(self.timestamp).split('.')[0].split(" ")[1]

	def get_timestamp(self):
		return str(self.timestamp).split('.')[0]

	def get_borrower(self):
		return self.borrower.__str__()

	def get_lender(self):
		return self.lender.__str__()

	def get_tool(self):
		return self.tool.__str__()

	def get_start_time(self):
		return str(self.start_date)

	def get_end_time(self):
		return str(self.end_date)