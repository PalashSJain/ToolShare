from django.contrib.auth import authenticate, login as auth_login, \
    REDIRECT_FIELD_NAME, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import deprecate_current_app
from django.contrib.sites.shortcuts import get_current_site
from django.core.context_processors import csrf
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse_lazy
from django.http.response import HttpResponseRedirect
from django.shortcuts import render, render_to_response, redirect, resolve_url, \
    get_object_or_404
from django.template.context import RequestContext
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.edit import UpdateView

from tool_share.forms import *
from tool_share.models import CustomUser
from django.contrib.auth.forms import PasswordChangeForm

tool_share_login_url = reverse_lazy("landing")


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # entered form-data is validated against form-class rules
            # save user and sharezone to db
            person = form.save()
            # redirect to home page
            token = {}
            token["first_name"] = person.first_name
            person = authenticate(username=form.cleaned_data['username'],
                                  password=form.cleaned_data['password1'],
                                  )
            auth_login(request, person)
            messages.success(request, "Registration successful.")
            return redirect("home")
        else:
            messages.error(request, "Registration failed.", extra_tags="danger")
    else:
        form = CustomUserCreationForm()
    token = {}
    token.update(csrf(request))
    token['form'] = form
    return render_to_response('user/login-new.html', token, context_instance=RequestContext(request))


'''
def register_complete(request):
	return render_to_response("registration/registration_complete.html, context_instance=RequestContext(request)")
'''


@login_required(login_url=tool_share_login_url)
def profile(request):
    token = {}
    person = CustomUser.objects.filter(id=request.user.id).values()[0]
    for key in person:
        token[key] = person[key]
    return render_to_response('user/profile.html', token, context_instance=RequestContext(request))


@login_required(login_url=tool_share_login_url)
def editprofile(request):
    if request.method == 'POST':

        form = CustomUserEditForm(request.POST,request.FILES,instance=request.user)
        if form.is_valid():
            #form is valid, user has left shed successfully
            try:
                form.save()
            except Exception as e:
                print(e)
            remindermsg=form.instance.get_join_zone_msgs()
            messages.success(request, "Profile successfully updated! "+remindermsg)
            return HttpResponseRedirect(resolve_url("profile"))
        else:
            messages.error(request, "Failed to update profile.", extra_tags="danger")
    else:
        form = CustomUserEditForm(instance=request.user)
    token = {}
    token['user'] = request.user
    token['form'] = form
    token['first_name'] = request.user.first_name
    token['intialPP']=form.initial['picture_path']
    return render(request, 'user/edit_profile.html', token)


def landing(request):
    token = {}
    token.update(csrf(request))
    return render_to_response("user/login-new.html", token, context_instance=RequestContext(request))


@login_required(login_url=tool_share_login_url)
def password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            person = form.save()
            update_session_auth_hash(request, person)  # Important!
            messages.success(request, "Password successfully changed!")
            return HttpResponseRedirect(resolve_url("home"))
        else:
            messages.error(request, "Failed to update password.", extra_tags="danger")
    else:
        form = PasswordChangeForm(request.user)
    token = {}
    token['user'] = request.user
    token['form'] = form
    token['first_name'] = request.user.first_name
    return render(request, 'user/edit_password.html', token)


@deprecate_current_app
@sensitive_post_parameters()
@csrf_protect
@never_cache
def login(request, template_name='user/login-new.html', redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm, extra_context=None):
    redirect_to = request.POST.get(redirect_field_name,
                                   request.GET.get(redirect_field_name, ''))

    if request.method == "POST":
        form = authentication_form(request, data=request.POST)
        if form.is_valid():
            # Ensure the user-originating redirection url is safe.
            if not is_safe_url(url=redirect_to, host=request.get_host()):
                redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

            # Okay, security check complete. Log the user in.
            auth_login(request, form.get_user())

            if form.get_user().is_admin:
                redirect_to = "/admin/login/"

            return HttpResponseRedirect(redirect_to)
        else:
            messages.error(request, "Authentication failed. Please try again.", extra_tags="danger")
            return redirect("/landing/")
    else:
        form = authentication_form(request)

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }
    if extra_context is not None:
        context.update(extra_context)

    return TemplateResponse(request, template_name, context)
