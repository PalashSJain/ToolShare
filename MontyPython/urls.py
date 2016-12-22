from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views
from django.core.urlresolvers import reverse
from tool_share import views as cust_view
from tool_share.forms import LoginForm
from django.contrib.auth.views import password_change, password_change_done

urlpatterns = [
	# static and media (images)
	url(r'^uploads/(?P<path>.*)$', 'django.views.static.serve', {
		'document_root': settings.MEDIA_ROOT,
	}),
	url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {
		'document_root': settings.STATIC_ROOT,
	}),

    url(r'^$', cust_view.home, name='home'),
    url(r'^admin/', admin.site.urls),

	url(r'^landing/$', cust_view.landing, name="landing"),
	url(r'^landing$', cust_view.landing, name="landing"),
	url(r'^login/$', cust_view.login, name="login"),
    url(r'^logout/$', views.logout, {'next_page': '/landing/'}, name="logout"),
    url(r'^register/$', cust_view.register, name='register'),

    # Profile URLs
    url(r'^profile/$', cust_view.profile, name='profile'),
    url(r'^profile/edit/$', cust_view.editprofile, name='profile_edit'),

    url(r'^profile/edit/password/$', cust_view.password_change, name='password_change'),
#   url(r'^deleting_user/$', cust_view.deleting_user, name='deleting_user'),

	# ------------------Notes------------------#
	url(r'^notes/$', cust_view.showNotes, name='show_notes'),

    #------------------Shed------------------#
    url(r'^shed/inventory/$', cust_view.viewInventory, name='shed_inventory'),
	url(r'^shed/stats/$', cust_view.viewStats, name='stats'),
	url(r'^shed/createshed/$', cust_view.createShed, name='create_shed'),

	# shed cordinator
	url(r'^viewshedusers/$', cust_view.viewshedusers, name='viewshedusers'),
	url(r'^makeshedcoordinator/(?P<userid>[0-9]+)', cust_view.makeshedcoordinator, name='makeshedcoordinator'),
	url(r'demotetouser/(?P<userid>[0-9]+)/$', cust_view.demotetouser, name='demotetouser'),
	url(r'deleteuser/(?P<userid>[0-9]+)/$', cust_view.deleteuser, name='deleteuser'),
	url(r'^shed/shed_details/$', cust_view.shed_details, name='shed_details'),
	url(r'^shed/edit_shed_details/$',cust_view.edit_shed_detail,name='edit_shed_detail'),
	url(r'^shed/save_shed_detail/(?P<newAdd>[\w\- ]+)/$',cust_view.save_shed_detail,name='save_shed_detail'),

	# super user
	url(r'^superuser/superuser_home/$', cust_view.superuser_home, name='superuser_home'),
	url(r'^superuser/view_allusers/$', cust_view.view_allusers, name='view_allusers'),
	url(r'^superuser/viewallsheds/$', cust_view.viewallsheds, name='viewallsheds'),
	url(r'^superuser/viewalltools/$', cust_view.viewalltools, name='viewalltools'),
	url(r'^superuser/delete_tool_superuser/(?P<tool_id>[0-9]+)/$', cust_view.delete_tool_superuser, name='delete_tool_superuser'),
	url(r'^superuser/edit_shed_details_superuser/(?P<shed_id>[0-9]+)/$', cust_view.edit_shed_details_superuser, name='edit_shed_details_superuser'),
	url(r'^superuser/save_shed_detail_superuser/(?P<add>[\w\- ]+)/(?P<shed_city>[\w\- ]+)/$', cust_view.save_shed_detail_superuser, name='save_shed_detail_superuser'),
	url(r'^superuser/delete_shed_superuser/(?P<shed_id>[0-9]+)/$', cust_view.delete_shed_superuser, name='delete_shed_superuser'),
	url(r'^superuser/make_super/(?P<user_id>[0-9]+)/$', cust_view.make_super, name='make_super'),
	url(r'^superuser/delete_user_superuser/(?P<user_id>[0-9]+)/$', cust_view.delete_user_superuser, name='delete_user_superuser'),
	url(r'^superuser/make_coordinator_superuser/(?P<user_id>[0-9]+)/$', cust_view.make_coordinator_superuser, name='make_coordinator_superuser'),
	url(r'^superuser/demote_to_user_superuser/(?P<user_id>[0-9]+)/$', cust_view.demote_to_user_superuser, name='demote_to_user_superuser'),

	# ------------------Reservation-----------------#
	# My Borrowed Tools List
	url(r'^myborrowlist/$', cust_view.myBorrowList, name="my_borrow_list"),
	url(r'^mylendlist/$', cust_view.myLendList, name="my_lend_list"),

	# Owner
	url(r'approval/(?P<resv_id>[0-9]+)/$', cust_view.resvApproval, name='approval'),
	url(r'[mytools|shedtools]/blockeddates/(?P<tool_id>[0-9]+)/$', cust_view.borrowTool, name='blocked_dates'),
    # status update
	url(r'(?P<resv_id>[0-9]+)/updatereservation/(?P<status>[0-6])/',cust_view.updateReservation,name='update_reservation'),

	# Select a tool to borrow
	url(r'borrowtoolrequest/(?P<tool_id>[0-9]+)/$', cust_view.borrowTool, name='borrow_tool'),
	# Confirm a tool
	url(r'borrowtoolrequest/confirm/(?P<resv_id>[0-9]+)/$',cust_view.confirmBorrowTool,name='confirm_borrow_tool'),
	
    #------------------Tool------------------#
    # tool details
	url(r'^mytools/(?P<tool_item_id>[0-9]+)/$', cust_view.myToolDetails, name='my_tool_details'),
	url(r'^tools/(?P<tool_id>[0-9]+)/$', cust_view.toolDetails, name='tool_details'),

    # owner of tool
    url(r'^deletetool/(?P<tool_id>[0-9]+)/$', cust_view.delete_tool, name='delete_tool'),
    url(r'^edittool/(?P<tool_id>[0-9]+)/$', cust_view.edit_tool, name='edit_tool'),
	url(r'^addtool/$', cust_view.edit_tool, name="add_tool"),
	url(r'^mytools/$', cust_view.myTools, name='my_tools'),
    # Tool status updates
	url(r'^verifycondition/(?P<tool_id>[0-9]+)/$',cust_view.verifyCondition,name='verify_condition'),
	url(r'(?P<tool_id>[0-9]+)/updateactivation/(?P<status>[0-1])/',cust_view.updateActivation,name='update_activation'),
	url(r'(?P<tool_id>[0-9]+)/updatepossession/(?P<status>[0-2])/',cust_view.updatePossession,name='update_possession'),

	url(r'^updatenotificationvisittime/$', cust_view.updateNotificationVisitTime, name='update_time'),
]

handler400 = cust_view.bad_request
handler403 = cust_view.permission_denied
handler500 = cust_view.server_error
handler404 = cust_view.page_not_found
