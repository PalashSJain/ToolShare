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
from django.http.response import HttpResponseRedirect, HttpResponseForbidden, HttpResponse
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
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError

from django.core import serializers
import json
from django.forms.models import model_to_dict

tool_share_login_url = reverse_lazy("landing")

user_nav_links = [{'title': 'Browse', 'link' : ''},
    {'title': 'My Sharing', 'link' : 'mytools/'},
    {'title': 'My Shed', 'link' : 'shed/'},
    {'title': 'Notifications', 'link' : 'notes/'},
    {'title': 'Profile', 'link' : 'profile/'},
    {'title': 'Logout', 'link' : 'logout/'},]

user_side_links = [{'title': 'HOME', 'link' : ''},
    {'title': 'ADD TOOL', 'link' : 'addtool/'},
    {'title': 'MY TOOLS', 'link' : 'mytools/'},
    {'title': 'BORROWED TOOLS', 'link' : 'myborrowlist/'},
    {'title': 'PROFILE', 'link' : 'profile/'},
    {'title': 'SHED', 'link' : 'shed/'},]

user = {
    'side_links' : user_side_links,
    'nav_links' : user_nav_links,
    }

@login_required(login_url=tool_share_login_url)
def myTools(request):
    query = Q(ownedBy=request.user)
    if request.user.is_coordinator:
        q = Q(pickupDropLoc=ToolItem.SHED) & Q(ownedBy__zip_code=request.user.zip_code) & Q(possession=ToolItem.RETURNED)
        query = query | q

    tools = ToolItem.objects.filter(query)
    token=user
    token["first_name"] = request.user.first_name
    token['tools']=tools
    token['user']=request.user
    return render_to_response('tools/tools-owner-list.html', token, context_instance=RequestContext(request))

@login_required(login_url=tool_share_login_url)
def myToolDetails(request, tool_item_id):
    tool = ToolItem.objects.get(id=tool_item_id)
    token={}
    token['user'] = request.user
    token['tool']=tool
    token['form']=VerifyToolForm(instance=tool)
    token.update(csrf(request))
    
    return render_to_response('tools/my-tool-details.html', token, context_instance=RequestContext(request))

@login_required(login_url=tool_share_login_url)
def toolsList(request):
    token = user
    token["first_name"] = request.user.first_name
    tools = ToolItem.objects.all()
    return render_to_response('user/toolslist.html', {'tools':tools}, context_instance=RequestContext(request))

@login_required(login_url=tool_share_login_url)
def borrowTool(request,tool_id):
    token=user
    token["first_name"] = request.user.first_name
    tool = ToolItem.objects.get(id=tool_id)
    token['tool'] = tool
    token['pickupLocation'] = tool.get_tool_pickup_address()

    if request.method == 'POST':
        form = CreateReservationForm(request.POST) # creates form from request-data

        # fill in model data that doesn't appear on the form, so validate can use it
        resv = form.instance
        resv.tool = tool
        resv.borrower = request.user
        if tool.ownedBy == request.user:
            resv.resv_type=Reservation.BLOCKOUT
        elif tool.pickupDropLoc == tool.SHED:
            resv.resv_type=Reservation.APPROVED
        else:
            resv.resv_type=Reservation.REQUESTED

        if form.is_valid():
            form.save() # copy form-data into instance
            if resv.resv_type == Reservation.BLOCKOUT:
                Reservation.cancel_and_reject_lending_conflicts(resv.get_same_tool_and_time_conflicts())
                return redirect(resolve_url('my_tools'))
            else:
                resv.make_resv_note()
                return redirect(resolve_url('confirm_borrow_tool',str(resv.pk) ))
    else:
        form = CreateReservationForm()

    if tool.ownedBy == request.user:
        token['btn_text']='Add Blockout'
        token['page_title']='Create Blockout'
    elif tool.pickupDropLoc == tool.SHED:
        token['btn_text']='Confirm Reservation'
        token['page_title']='Create Reservation'
    else:
        token['btn_text']='Request Reservation'
        token['page_title']='Create Reservation'

    token["unavailabilities"]=tool.get_unavailabilities(request.user)

    token.update(csrf(request))
    token['form'] = form
    token['form_action']=resolve_url('borrow_tool',str(tool.id) )
    return render_to_response('reservation/resv-add.html', token, context_instance=RequestContext(request))

@login_required(login_url=tool_share_login_url)
def confirmBorrowTool(request,resv_id):
    token=user
    token["first_name"] = request.user.first_name

    resv=Reservation.objects.get(id=resv_id)
    tool=ToolItem.objects.get(id=resv.tool.pk)
    token['resv']=resv
    token['tool']=tool
    return render_to_response('reservation/confirmationborrowing.html', token, context_instance=RequestContext(request))


@login_required(login_url=tool_share_login_url)
def edit_tool(request, tool_id=None):
    token = {}
    token["first_name"] = request.user.first_name
    token["path"] = request.path
    existingTool = ToolItem(ownedBy=request.user)
    if tool_id:
        existingTool = ToolItem.objects.get(pk=tool_id)
        if existingTool:
            if existingTool.ownedBy != request.user:
                raise PermissionDenied

    if request.method == 'POST':
        form = AddToolForm(request.POST,request.FILES,instance=existingTool)
        
        token['success'] = 1
        if form.is_valid():
            form.save()
            messages.success(request, "Tool Saved.")
            return redirect(resolve_url("my_tools"))
    else:
        form = AddToolForm(instance=existingTool)
    token.update(csrf(request))
    token['form'] = form
    token['intialPP']=form.initial['picture_path']
    return render_to_response('tools/tool-edit.html', token, context_instance=RequestContext(request))


@login_required(login_url=tool_share_login_url)
def toolDetails(request, tool_id):
    #include share and borrow here
    
    token=user
    token["first_name"] = request.user.first_name
    tool = ToolItem.objects.filter(id=tool_id).values('id', 'ownedBy__first_name', 'ownedBy__last_name', 'ownedBy__address', 'title', 'picture_path', 'description', 'special_instructions', 'condition', 'possession', 'pickupDropLoc', 'activation')[0]
    token['tool']=tool
    if tool['pickupDropLoc'] == ToolItem.SHED:
        shed = Sheds.objects.filter(zip_code=request.user.zip_code).first()
        if shed is not None:
            tool['ownedBy__address'] = getattr(shed, 'street_address')
    token["CONDITION_CHOICES"] = ToolItem.CONDITION_CHOICES
    token["ACTIVATED"] = ToolItem.ACTIVATED
    return render_to_response('tools/tool-detail.html', token, context_instance=RequestContext(request))


@login_required(login_url=tool_share_login_url)
def resvApproval(request, resv_id=None):
    token = {}
    token["first_name"] = request.user.first_name

    existingResv = Reservation.objects.get(pk=resv_id)
    if ToolItem.objects.get(pk=existingResv.tool.pk).ownedBy != request.user:
        raise PermissionDenied

    if request.method == 'POST':
        form = ReservationApprovalForm(request.POST,instance=existingResv)
        if form.is_valid():
            resv=form.save()
            resv.make_resv_note()
            if resv.resv_type == Reservation.APPROVED:
                # reject other conflicting requests
                Reservation.update_lending_requests(resv.get_same_tool_and_time_conflicts(),Reservation.REJECTED)
            return redirect(resolve_url("my_lend_list"))
    else:
        form = ReservationApprovalForm(instance=existingResv)
    token.update(csrf(request))
    token['form'] = form
    return render_to_response('reservation/approval.html', token, context_instance=RequestContext(request))


@login_required(login_url=tool_share_login_url)
def delete_tool(request, tool_id=None):
    token = {}
    token["first_name"] = request.user.first_name

    existingTool = ToolItem.objects.get(pk=tool_id)
    if existingTool.ownedBy != request.user:
        raise PermissionDenied

    [isRemoved,errormsgs]=existingTool.removetool()
    if isRemoved:
        messages.success(request, "Tool successfully deleted!")
    else:
        messages.error(request, "Failed to delete tool. "+errormsgs, extra_tags="danger")

    return redirect(resolve_url("my_tools"))