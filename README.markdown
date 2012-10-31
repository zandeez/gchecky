What is gchecky
===============
gchecky is a Python implementation of the Google Checkout XML API originally found on Google Code here: http://code.google.com/p/gchecky/

However, it's not been updated for a long time, and didn't do the things I wanted it to, so I forked the project here.
My additions include an implementation of the patch submitted here: http://code.google.com/p/gchecky/issues/detail?id=42 as well as a few of my own fixes.

Installation
============
Installation should be just a case of typing this (if you have pip installed):
	$ pip install git+http://github.com/zandeez/gchecky.git

Using
=====
Documentation is sparse, but the original site has some examples that got me started. The first thing to note is that all the XML tags have a
corresponding class in gchecky.model, and you can build and iterate the XML trees accoringly.

Overriding The Mesasge Handlers
-------------------------------
You will need to provide your own implementation of what to do for each notification message type. The message below show a basic implementation
handling only new order confirmations:

	from gchecky.controller import Controller
	from gchecky import model as gmodel
	
	class MyController(Controller):
		def handle_new_order(self, message, order_id, context, order=None):
			# do something with the order
			return gmodel.ok_t()

Singleton Controller Instance
-----------------------------
The documentation insists on a singleton instance of the controller, so put it somewhere sensible:

	controller = MyController('MERCHANT_ID', 'MERCHANT_KEY', is_sandbox=True, current="GBP")

Building and Submitting your Cart
---------------------------------
You'll need to build up the class hirachy for a checkout-shopping-cart message. The basic idea goes as follows:

	from gchecky import model as gmodel
	
	cart = gmodel.checkout_shopping_cart_t(shopping_cart = gmodel.shopping_cart_t())
	cart.checkout_flow_support = gmodel.checkout_flow_support_t()
	cart.shopping_cart.items = [
		gmodel.item_t(
			name = "ITEM_NAME,"
			description = "ITEM_DESCRIPTION",
			unit_price = gmodel.price_t(value=10.0,currency='GBP'),
			quantity = 7,
		)
	]
	
Then of course you need to submit the order to Google Checkout using the static instance of your controller:

	order = controller.prepare_server_order(cart).submit()
	
If all was successful, order.redirect_url will contain a URL that you should redirect the user to to complete the order.

Handling the Notifications
--------------------------
The actual process of receive the XML has to be partially delegated ot te web framework of your choice, and will depend on your notification options in 
the Google Checkout control panel. Both serial number and XML notifications are supported, although the process is different for each.

Serial number notifications are sent as a key-value pair where the key is serial-number. This indicates the serial number of the notification that we
should retrive from the server. This can be retrieved like so:

	result = controller.process_notification(serial)
	
For xml, you just need to pass the entire raw post data like so:

	result = controller.receive_xml(RAW_POST_DATA)
	
And that's pretty much that!

Django Example
==============
This is a very basic implementation treated as a single file for Django of everthing discussed above.

	from gchecky.controller import Controller
	from gchecky import model as gmodel
	from django.conf import settings
	from django.views.decorators.csrf import csrf_exempt
	from django.http import HttpResponse
	from django.shortcuts import redirect
	
	class MyController(Controller):
		def handle_new_order(self, message, order_id, context, order=None):
			# do something with the order
			return gmodel.ok_t()
	
	controller = MyController(settings.GC_ID, settings.GC_KEY,
		is_sandbox=settings.GC_SANDBOX, currency=settings.GC_CURRENCY)
	
	def checkout(request):
		cart = gmodel.checkout_shopping_cart_t(shopping_cart = gmodel.shopping_cart_t())
		cart.checkout_flow_support = gmodel.checkout_flow_support_t()
		cart.shopping_cart.items = [
			gmodel.item_t(
				name = "ITEM_NAME,"
				description = "ITEM_DESCRIPTION",
				unit_price = gmodel.price_t(value=10.0,currency='GBP'),
				quantity = 7,
			)
		]
		
		order = controller.prepare_server_order(cart).submit()
		return redirect(order.redirect_url)
	
	@csrf_exempt
	def google_checkout_notification(request):
		if request.META["CONTENT_TYPE"] == "application/x-www-form-urlencoded":
			serial = request.REQUEST['serial-number']
			result = controller.process_notification(serial)
		else:
			result = controller.receive_xml(request.raw_post_data)
		
		if result.__class__ == gmodel.ok_t:
				result = gmodel.notification_acknowledgment_t(serial_number=serial)
			
		return HttpResponse(result, content_type="application/xml; charset=UTF-8")
