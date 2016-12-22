from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login, get_user, \
	REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import deprecate_current_app
from django.contrib.sites.shortcuts import get_current_site
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse, reverse_lazy
from django.db import connection
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render, render_to_response, redirect, resolve_url, \
	get_object_or_404
from django.template.context import RequestContext
from django.template.context_processors import request
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.edit import UpdateView

from django.db.models import Q
from tool_share.forms import *
from tool_share.models import ToolItem, CustomUser
from django.db.models import Count
from django.core.exceptions import PermissionDenied

tool_share_login_url = reverse_lazy("landing")

user_nav_links = [{'title': 'Browse', 'link' : ''},
	{'title': 'My Sharing', 'link' : 'mytools/'},
	{'title': 'My Shed', 'link' : 'shed/'},
	{'title': 'Notifications', 'link' : 'notes/'},
	{'title': 'Profile', 'link' : 'profile/'},
	{'title': 'Logout', 'link' : 'logout/'},]

# user_side_links = [{'title': 'HOME', 'link' : ''},
#     {'title': 'ADD TOOL', 'link' : 'addtool/'},
#     {'title': 'MY TOOLS', 'link' : 'mytools/'},
#     {'title': 'BORROWED TOOLS', 'link' : 'myborrowlist/'},
#     {'title': 'PROFILE', 'link' : 'profile/'},
#     {'title': 'SHED', 'link' : 'shed/'},]

user = {
	'side_links' : [],
	'nav_links' : user_nav_links,
	}


@login_required(login_url=tool_share_login_url)
def createShed(request):
	token = user
	token["first_name"] = request.user.first_name
	if request.method == 'POST':
		shed,wasCreated=Sheds.objects.get_or_create(zip_code=request.user.zip_code)
		form = CreateShedForm(request.POST,instance=shed)
		if form.is_valid():
			form.save()

			member = get_user(request)
			member.is_coordinator = True
			member.save()

			return redirect("/shed/stats/",token)
	else:
		form = CreateShedForm({'zip_code' : request.user.zip_code})
	token.update(csrf(request))
	token['form'] = form
	return render_to_response('shed/create-shed.html',token, context_instance=RequestContext(request))

@login_required(login_url=tool_share_login_url)
def viewInventory(request):
	token=user
	token["first_name"] = request.user.first_name
	active_my_shed = Q(ownedBy__zip_code=request.user.zip_code) & Q(activation=ToolItem.ACTIVATED) & Q(pickupDropLoc=ToolItem.SHED)
	tools = ToolItem.objects.filter(active_my_shed)
	token['tools']=tools
	req_user = request.user
	token['req_user'] = req_user
	request_user = CustomUser.objects.get(id=req_user.id)
	token['page_title']='Community Shed Inventory'
	shed = Sheds.objects.filter(zip_code=request.user.zip_code).first()
	token['add_shed_btn']= shed is None

	token['forms']=[]
	for index in range(len(tools)):
		token['forms'].append(VerifyToolForm(instance=tools[index]))
	token.update(csrf(request))

	token["isCoordinator"]=request.user.is_coordinator
	is_co = request_user.is_coordinator
	token['is_coordinator']=is_co
	if is_co == 1:
		return render_to_response('shed/shed-inventory.html', token, context_instance=RequestContext(request))
	elif is_co == 0:
		return HttpResponseRedirect('/shed/stats/',token)
		# return render_to_response('shed_management/viewshedusers.html',token)

def listToString(list):
	str=""
	for item in list:
		str += item.__str__() + ", "
	return str

@login_required(login_url=tool_share_login_url)
def viewStats(request):
	token=user
	token["first_name"] = request.user.first_name

	#list of statistics
	topN=3
	shedusers=CustomUser.objects.filter(zip_code=request.user.zip_code)
	activeshedtools=ToolItem.objects.filter(ownedBy__zip_code=request.user.zip_code).filter(activation=ToolItem.ACTIVATED)
	acceptedresvs=Reservation.objects.filter(tool__ownedBy__zip_code=request.user.zip_code).filter(resv_type=Reservation.APPROVED)
	lendersmosttools=shedusers.filter(toolitem__activation=ToolItem.ACTIVATED).annotate(num_tools=Count('toolitem')).order_by('-num_tools')
	toolsmostresvs=activeshedtools.filter(reservation__resv_type=Reservation.APPROVED).annotate(num_resvs=Count('reservation')).order_by('-num_resvs')
	borrowersmostresvs = shedusers.filter(reservation__resv_type=Reservation.APPROVED).annotate(num_resvs=Count('reservation')).order_by('-num_resvs')
	lendersmostresvs=shedusers.filter(toolitem__activation=ToolItem.ACTIVATED,toolitem__reservation__resv_type=Reservation.APPROVED).annotate(num_resvs=Count('reservation')).order_by('-num_resvs')
	stats = [
	["Shed Coordinators", shedusers.filter(is_coordinator=True).count],
	["Users", shedusers.count],
	["Active Tools", activeshedtools.count],
	["Shared from Home", activeshedtools.filter(pickupDropLoc=ToolItem.HOME).count],
	["Shared from Shed", activeshedtools.filter(pickupDropLoc=ToolItem.SHED).count],
	["Accepted Reservations", acceptedresvs.count],
	["Top "+str(topN)+" Lenders With Most Tools", listToString(lendersmosttools[:topN]), True, True],
	["Top "+str(topN)+" Tools With Most Reservations", listToString(toolsmostresvs[:topN]), True, True],
	["Top "+str(topN)+" Borrowers With Most Reservations", listToString(borrowersmostresvs[:topN]), True, True],
	["Top "+str(topN)+" Lenders With Most Reservations", listToString(lendersmostresvs[:topN]), True, True],
	]
	token['stats']=stats

	# used for UI
	token['page_title']='Zone Statistics'
	query = Q(ownedBy__zip_code=request.user.zip_code) & Q(activation=ToolItem.ACTIVATED) & Q(pickupDropLoc=ToolItem.SHED)
	tools = ToolItem.objects.filter(query)
	token['tools']=tools
	token["isCoordinator"]=request.user.is_coordinator
	token['add_shed_btn']= False #don't need a shed to view the stats
	return render_to_response('shed/stats.html', token, context_instance=RequestContext(request))


@login_required(login_url=tool_share_login_url)
def shed_details(request):
	token=user
	sheds = Sheds.objects.filter(zip_code=request.user.zip_code).first()
	token['shed_detail']=sheds
	token['page_title']='Community Shed Details'
	token['add_shed_btn']= sheds is None
	token["isCoordinator"]=request.user.is_coordinator
	return render_to_response('shed/shed_details.html', token)


@login_required(login_url=tool_share_login_url)
def edit_shed_detail(request):
	token=user
	token.update(csrf(request))
	shed_zipcode = request.user.zip_code
	shed_detail = Sheds.objects.get(zip_code=shed_zipcode)
	token['shed_detail'] = shed_detail
	return render_to_response('shed/edit_shed_detail.html', token)

@login_required(login_url=tool_share_login_url)
def save_shed_detail(request,newAdd):
	token=user
	shed_zipcode = request.user.zip_code
	shed_detail = Sheds.objects.get(zip_code=shed_zipcode)
	shed_detail.street_address=newAdd
	shed_detail.save()
	token['shed_detail'] = shed_detail
	return render_to_response('shed/shed_details.html', token)

@login_required(login_url=tool_share_login_url)
def viewshedusers(request):
	users = CustomUser.objects.filter(zip_code=request.user.zip_code)
	token=user
	token["first_name"] = request.user.first_name
	token["req_user"] = request.user

	token['users']=users
	token["isCoordinator"]=request.user.is_coordinator

	token['page_title'] = 'Zone Members'
	token['add_shed_btn']= False #don't need a shed to view the members
	return render_to_response('shed_management/viewshedusers.html',token,context_instance=RequestContext(request))

@login_required(login_url=tool_share_login_url)
def makeshedcoordinator(request,userid):
	user1=CustomUser.objects.get(id=userid)

	[wasSuccess,errormsgs]=user1.promote_to_coordinator()
	if wasSuccess:
		messages.success(request, "Member successfully promoted to coordinator!")
	else:
		messages.error(request, "Failed to promote user to coordinator. "+errormsgs, extra_tags="danger")
	print('about to run method')
	return redirect(resolve_url("viewshedusers"))

@login_required(login_url=tool_share_login_url)
def demotetouser(request,userid):
	user1 = CustomUser.objects.get(id=userid)

	[wasSuccess,errormsgs]=user1.demote_from_coordinator()
	if wasSuccess:
		messages.success(request, "Coordinator successfully demoted!")
	else:
		messages.error(request, "Failed to demote coordinator. "+errormsgs, extra_tags="danger")
	return redirect(resolve_url("viewshedusers"))

@login_required(login_url=tool_share_login_url)
def deleteuser(request,userid):
	deleteusername=CustomUser.objects.get(id=userid)
	[wasSuccess,errormsgs]=deleteusername.leavezone()
	if wasSuccess:
		deleteusername.delete()
		messages.success(request, "Member successfully deleted!")
		if deleteusername == request.user:
			return redirect(resolve_url("logout"))
	else:
		messages.error(request, "Failed to delete member. "+errormsgs, extra_tags="danger")
	return redirect(resolve_url("viewshedusers"))

