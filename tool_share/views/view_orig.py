from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login, get_user, \
	REDIRECT_FIELD_NAME,update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import deprecate_current_app
from django.contrib.sites.shortcuts import get_current_site
from django.core.urlresolvers import reverse, reverse_lazy
from django.db import connection
from django.http.response import HttpResponseRedirect, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, render_to_response, redirect, resolve_url, \
	get_object_or_404
from django.template.context import RequestContext
from django.template.context_processors import request, csrf
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.edit import UpdateView
from django.contrib import messages
from django.db.models import Q
from tool_share.forms import *
from tool_share.models import ToolItem, CustomUser
from django.core.exceptions import PermissionDenied
import json

tool_share_login_url = reverse_lazy("landing")

user_nav_links = [{'title': 'Browse', 'link': ''},
				  {'title': 'My Sharing', 'link': 'mytools/'},
				  {'title': 'My Shed', 'link': 'shed/'},
				  {'title': 'Notifications', 'link': 'notes/'},
				  {'title': 'Profile', 'link': 'profile/'},
				  {'title': 'Logout', 'link': 'logout/'}, ]

user_side_links = [{'title': 'HOME', 'link': ''},
				   {'title': 'ADD TOOL', 'link': 'addtool/'},
				   {'title': 'MY TOOLS', 'link': 'mytools/'},
				   {'title': 'BORROWED TOOLS', 'link': 'myborrowlist/'},
				   {'title': 'PROFILE', 'link': 'profile/'},
				   {'title': 'SHED', 'link': 'shed/'}, ]

user = {
	'side_links': user_side_links,
	'nav_links': user_nav_links,
}


# 400
def bad_request(request):
	return page_not_found(request)


# 404
def page_not_found(request):
	token = {}
	token["path_info"] = request.path_info
	# token["first_name"] = request.user.first_name
	return render_to_response("navigation/404.html", token)


# 500
def server_error(request):
	token = {}
	# token["first_name"] = request.user.first_name
	return render_to_response("navigation/500.html", token)


# 403
def permission_denied(request):
	token = {}
	token["first_name"] = request.user.first_name
	token["message"] = "You do not have sufficient permissions to view this page."
	return render_to_response("navigation/403.html", token)


@login_required(login_url=tool_share_login_url)
def home(request):
	token = user
	token["first_name"] = request.user.first_name
	token["user"] = request.user
	is_super = request.user.is_superuser
	if (is_super == 1):
		return render_to_response("superuser/superuser_home.html", token)
	else:
		query = Q(ownedBy__zip_code=request.user.zip_code) & Q(activation=ToolItem.ACTIVATED)
		# get user preferences and is_coordinator
		user_id = get_user(request).pk
		# filter notes by those TODO
		# if user.preferences == CustomUser.SHED_NEWS:
		# notes = Notification.objects.filter(person_to_notify_id=(user.pk or user.zip_code))

		token['tools'] = ToolItem.objects.filter(query).exclude(ownedBy=request.user)
		token['page_title'] = "Your Neighbor's Shared Tools"
		token.update(csrf(request))

	return render_to_response("tools/tools-browse-list.html", token, context_instance=RequestContext(request))


@login_required(login_url=tool_share_login_url)
def superuser_home(request):
	token = user
	token['firstname'] = request.user.first_name
	return render_to_response("superuser/superuser_home.html", token)


# @login_required(login_url=tool_share_login_url)
# def deleting_user(request):
#     token = user
#     token["first_name"] = request.user.first_name
#     person = CustomUser.objects.filter(id=request.user.id)[0]
#     
#     # TODO: borrowedBy has been removed from the ToolItem model.
#     tools = ToolItem.objects.filter(borrowedBy=person)
#     if tools:
#         print("Account cannot be deleted: You have currently borrowed tools from someone.")
#     else:
#         CustomUser.objects.filter(id=request.user.id).delete()
#         return redirect("/logout")

@login_required(login_url=tool_share_login_url)
def updateActivation(request, tool_id, status):
	tool = ToolItem.objects.get(id=tool_id)
	tool.activation = int(status)
	tool.save()

	if (status == tool.DEACTIVATED):
		tool_and_time = Q(tool=tool) & Q(start_date__gt=date.today())
		Reservation.cancel_and_reject_lending_conflicts(tool_and_time)

	token = user
	return redirect(resolve_url('my_tools'))


@login_required(login_url=tool_share_login_url)
def verifyCondition(request,tool_id):
	existingTool = ToolItem.objects.get(pk=tool_id)
	if existingTool:
		if existingTool.ownedBy != request.user and not request.user.is_coordinator:
			raise PermissionDenied

		if request.method == 'POST':
			form = VerifyToolForm(request.POST)  # creates form from request-data
			if form.is_valid():
				con=form.cleaned_data['condition']
				print('condition is: '+str(con))
				existingTool.condition = con
				existingTool.save()
				return updatePossession(request,tool_id,ToolItem.VERIFIED_RETURNED)
	token = user
	token["first_name"]=request.user.first_name
	ref_url = request.META['HTTP_REFERER'].replace("http://localhost:8000", "")
	return redirect(ref_url, token)


@login_required(login_url=tool_share_login_url)
def updatePossession(request, tool_id, status):
	tool = ToolItem.objects.get(id=tool_id)
	tool.possession = int(status)
	tool.save()
	if tool.possession == tool.RETURNED:
		Notification.make_notification(note_type=Notification.TASK_VERIFY_TOOL_RETURNS, display_to=Notification.LENDER,
									   borrower=None, lender=tool.ownedBy, start_date=None, tool=tool,
									   end_date=None)
	token = user
	token["first_name"]=request.user.first_name

	if tool.possession == tool.VERIFIED_RETURNED:
		ref_url=request.META['HTTP_REFERER'].replace("http://localhost:8000","")
		return redirect(ref_url,token)

	return redirect(resolve_url('my_borrow_list'),token)


@login_required(login_url=tool_share_login_url)
def updateReservation(request, resv_id, status):
	resv = Reservation.objects.get(id=resv_id)
	resv.update_resv_type(int(status))

	token = user
	return redirect(resolve_url('my_borrow_list'))


@login_required(login_url=tool_share_login_url)
def showNotes(request):
	token = user
	token["first_name"] = request.user.first_name
	# get user preferences and is_coordinator
	user_id = get_user(request)
	# filter notes by those TODO
	# if user.preferences == CustomUser.SHED_NEWS:
	# notes = Notification.objects.filter(person_to_notify_id=(user.pk or user.zip_code))
	query = Q(display_to=user_id)  # | Q(person_to_notify_id=request.user.zip_code)
	notes = Notification.objects.filter(query).order_by('-pk')
	token['notes'] = notes
	notesCount = 0;

	userLastVisit = request.user.last_notification_visit
	for note in notes:
		if note.timestamp > userLastVisit:
			# print(note.timestamp)
			# print(userLastVisit)
			notesCount = notesCount + 1
	token['noti_count'] = notesCount;
	# display the notifications
	return render_to_response('notes/notes.html', token, context_instance=RequestContext(request))

@login_required(login_url=tool_share_login_url)
def updateNotificationVisitTime(request):
	request.user.last_notification_visit = datetime.now()
	request.user.save();
	return HttpResponse( json.dumps({}), content_type="application/json" )


@login_required(login_url=tool_share_login_url)
def myBorrowList(request):
	token = user
	my_borrowing = Q(borrower=request.user)
	time_or_my_possession = Q(end_date__gte=date.today()) | Q(tool__possession=ToolItem.PICKED_UP)
	resvs = Reservation.objects.filter(my_borrowing & time_or_my_possession)
	resvs.order_by('start_date')
	token['resvs'] = resvs
	token['user'] = get_user(request)
	return render_to_response('reservation/borrowlist.html', token, context_instance=RequestContext(request))


@login_required(login_url=tool_share_login_url)
def myLendList(request):
	token = user
	my_borrowing = Q(borrower=request.user)
	my_lending = Q(tool__ownedBy=request.user)
	future = Q(start_date__gte=date.today())

	resvs = Reservation.objects.filter(~my_borrowing & my_lending & future)
	resvs.order_by('start_date')
	token['resvs'] = resvs
	token['user'] = get_user(request)
	return render_to_response('reservation/lendlist.html', token, context_instance=RequestContext(request))


'''
SUPER USER FUNCTIONALITIES
'''


def superuser():
	def true_decorator(fn):
		def wrapper(*args, **kwargs):
			if args[0].user.is_superuser == CustomUser.SUPERUSER:
				return fn(*args, **kwargs)
			else:
				raise PermissionDenied()
		return wrapper
	return true_decorator


@superuser()
@login_required(login_url=tool_share_login_url)
def view_allusers(request):
	token = user
	userid = request.user.id
	allusers = CustomUser.objects.all().exclude(id=userid)
	token['allusers'] = allusers
	return render_to_response("superuser/view_allusers.html", token, context_instance=RequestContext(request))


@superuser()
@login_required(login_url=tool_share_login_url)
def viewallsheds(request):
	token = user
	allsheds = Sheds.objects.all()
	token['allsheds'] = allsheds
	return render_to_response("superuser/viewallsheds.html", token, context_instance=RequestContext(request))


@superuser()
@login_required(login_url=tool_share_login_url)
def viewalltools(request):
	token = user
	alltools = ToolItem.objects.all()
	token['alltools'] = alltools
	return render_to_response("superuser/viewalltools.html", token, context_instance=RequestContext(request))



@login_required(login_url=tool_share_login_url)
def delete_tool_superuser(request,tool_id):
	token = user
	selected_tool = ToolItem.objects.get(id=tool_id)
	[wasSuccess,errormsgs]=selected_tool.removetool()
	if wasSuccess:
		messages.success(request,"Tool successfully deleted!")
		return redirect(resolve_url("viewalltools"))
	else:
		messages.error(request,"Failed to delete tool. "+errormsgs,extra_tags="danger")
	return redirect(resolve_url("viewalltools"))


@superuser()
@login_required(login_url=tool_share_login_url)
def edit_shed_details_superuser(request,shed_id):
	token = user
	shed_detail = Sheds.objects.get(id=shed_id)
	token['shed_detail'] = shed_detail
	return render_to_response('superuser/edit_shed_detail_superuser.html', token)


@superuser()
@login_required(login_url=tool_share_login_url)
def save_shed_detail_superuser(request,add,shed_city):
	token=user
	shed_detail = Sheds.objects.get(city=shed_city)
	shed_detail.street_address = add
	shed_detail.save()
	messages.success(request,"Shed address updated successfully!")
	token['shed_detail'] = shed_detail
	return redirect(resolve_url("viewallsheds"))


@superuser()
@login_required(login_url=tool_share_login_url)
def delete_shed_superuser(request,shed_id):
	token = user
	shed_detail = Sheds.objects.get(id=shed_id)
	shed_detail.delete()
	messages.success(request, "Shed successfully deleted!")
	return redirect(resolve_url("viewallsheds"))


@superuser()
@login_required(login_url=tool_share_login_url)
def delete_user_superuser(request,user_id):
	token=user
	seleted_user = CustomUser.objects.get(id=user_id)
	[wasSuccess,errormsgs]=seleted_user.leavezone()
	if wasSuccess:
		seleted_user.delete()
		messages.success(request,"Member successfully deleted!")
	else:
		messages.error(request,"Failed to delete member. "+errormsgs,extra_tags="danger")
	return redirect(resolve_url("view_allusers"))


@superuser()
@login_required(login_url=tool_share_login_url)
def make_super(request,user_id):
	user_details = CustomUser.objects.get(id=user_id)
	user_details.is_superuser = True
	user_details.save()
	messages.success(request,"Member successfully promoted to Super User!")
	return redirect(resolve_url('view_allusers'))


@superuser()
@login_required(login_url=tool_share_login_url)
def make_coordinator_superuser(request,user_id):
	selected_user=CustomUser.objects.get(id=user_id)
	[wasSuccess,errormsgs]=selected_user.promote_to_coordinator()
	if wasSuccess:
		messages.success(request,"Member successfully promoted to coordinator!")
	else:
		messages.error(request,"Failed to promote user to coordinator. "+errormsgs,extra_tags="danger")
	return redirect(resolve_url('view_allusers'))


@superuser()
@login_required(login_url=tool_share_login_url)
def demote_to_user_superuser(request,user_id):
	selected_user=CustomUser.objects.get(id=user_id)
	[wasSuccess,errormsgs]=selected_user.demote_from_coordinator()
	if wasSuccess:
		messages.success(request,"Coordinator successfully demoted!")
	else:
		messages.error(request,"Failed to demote coordinator. "+errormsgs,extra_tags="danger")
	return redirect(resolve_url('view_allusers'))