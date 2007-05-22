from base64 import b64encode
import urllib2

from gchecky import gxml
from gchecky import model as gmodel

URL = 'https://%s.google.com/checkout/cws/v2/Merchant/%s/checkout'
BUTTON = 'http://%s.google.com/checkout/buttons/checkout.gif?merchant_id=%s&w=180&h=46&style=white&variant=text&loc=en_US'
HTML = """
<form method="POST" action="%s">
    <input type="hidden" name="cart" value="%s" />
    <input type="hidden" name="signature" value="%s" />
    <input type="image" src="%s" border="0" alt="Google Checkout" /> 
</form>
"""
SENDING_URL = 'https://checkout.google.com/checkout/cws/v2/Merchant/%s/request'
SANDBOX_SENDING_URL = 'https://sandbox.google.com/checkout/cws/v2/Merchant/%s/request'

class Controller:
    # Create the controller, specify all the needed information
    # such as merchant account credentials:
    #   - sandbox or production
    #   - google vendor ID
    #   - google merchant key
    def __init__(self, vendor_id, merchant_key, is_sandbox=True):
        self.vendor_id = vendor_id
        self.merchant_key = merchant_key
        self.is_sandbox = is_sandbox
        self.www_prefix = (is_sandbox and 'sandbox') or 'www'

    def sending_url(self):
        url_pattern = (self.is_sandbox and SANDBOX_SENDING_URL) or SENDING_URL
        return url_pattern % (self.vendor_id,)

    def send(self, msg):
        req = urllib2.Request(url=self.sending_url(),
                              data=msg)
        req.add_header('Authorization',
                       'Basic %s' % (b64encode('%s:%s' % (self.vendor_id,
                                                          self.merchant_key)),))
        req.add_header('Content-Type', ' application/xml; charset=UTF-8')
        req.add_header('Accept', ' application/xml; charset=UTF-8')
        try:
            response = urllib2.urlopen(req).read()
        except urllib2.HTTPError, error:
            response = error.fp.read()
        return response

    def send_message(self, message):
        msg = message.toxml()
        print '-----------'
        print msg
        print '-----------'
        return self.send(msg)

    def create_HMAC_SHA_signature(self, xml_text):
        import hmac, sha
        return hmac.new(self.merchant_key, xml_text, sha).digest()

    # Specify order_id to track the order
    # The order_id will be send back to us by google with order verification
    def prepare_order(self, order, order_id=None):
        cart = order.toxml()

        cart64 = b64encode(cart)
        signature64 = b64encode(self.create_HMAC_SHA_signature(cart))
        html = html_order()
        html.cart = cart64
        html.signature = signature64
        html.url = URL % (self.www_prefix, self.vendor_id)
        html.button = BUTTON % (self.www_prefix, self.vendor_id)
        html.xml = cart
        html.html = HTML % (html.url, html.cart, html.signature, html.button)
        return html

    def process_response(self, response):
        try:
            doc = gxml.Document.fromxml(response)
            print 'Result: %s' % (doc.__class__,)
            print '=============='
            print doc.toxml()
            if doc.__class__ != gmodel.request_received_t:
                if doc.__class__ != gmodel.error_t:
                    # OMG! Unknown message!
                    raise Exception, 'SEVERE ERROR! THE GCHECKY LIBRARY DOES NOT FUNCTION PROPERLY'
                msg = 'Error message from GCheckout API:\n%s' % (doc.error_message, )
                if doc.warning_messages:
                    tmp = ''
                    for warning in doc.warning_messages:
                        tmp += '\n%s' % (warning,)
                    msg += ('Additional warnings:%s' % (tmp,))
                print 'EXXXXXXXXXXXXXXXXCEPTION:' + msg
                raise Exception(msg)
        except Exception, exc:
            print '==================='
            print 'Exception: %s' % (exc,)
            print '==================='

    def archive_order(self, order_id):
        self.process_response(self.send_message(
            gmodel.archive_order_t(google_order_number=order_id)))
    def unarchive_order(self, order_id):
        self.process_response(self.send_message(
            gmodel.unarchive_order_t(google_order_number=order_id)))

    def send_buyer_message(self, order_id, message):
        self.process_response(self.send_message(gmodel.send_buyer_message_t(
            google_order_number = order_id,
            message = message,
            send_email = True
            )))

    def add_merchant_order_number(self, order_id, merchant_order_number):
        self.process_response(self.send_message(gmodel.add_merchant_order_number_t(
            google_order_number = order_id,
            merchant_order_number = merchant_order_number
            )))

    def add_tracking_data(self, order_id, carrier, tracking_number):
        self.process_response(self.send_message(gmodel.add_tracking_data_t(
            google_order_number = order_id,
            tracking_data = gmodel.tracking_data_t(carrier         = carrier,
                                                   tracking_number = tracking_number)
            )))

    def charge_order(self, order_id, amount):
        self.process_response(self.send_message(gmodel.charge_order_t(
            google_order_number = order_id,
            amount = gmodel.price_t(value = amount, currency = 'GBP')
            )))

    def refund_order(self, order_id, amount, reason, comment=None):
        self.process_response(self.send_message(gmodel.refund_order_t(
            google_order_number = order_id,
            amount = gmodel.price_t(value = amount, currency = 'GBP'),
            reason = reason,
            comment = comment or None
            )))

    def authorize_order(self, order_id, do_in_production=False):
        if do_in_production or self.is_sandbox:
            self.process_response(self.send_message(gmodel.authorize_order_t(
                google_order_number = order_id
            )))

    def cancel_order(self, order_id, reason, comment=None):
        self.process_response(self.send_message(gmodel.cancel_order_t(
            google_order_number = order_id,
            reason = reason,
            comment = comment or None
            )))

    def process_order(self, order_id):
        self.process_response(self.send_message(gmodel.process_order_t(
            google_order_number = order_id
            )))

    def deliver_order(self, order_id,
                      carrier = None, tracking_number = None,
                      send_email = None):
        tracking = None
        if carrier or tracking_number:
            tracking = gmodel.tracking_data_t(carrier         = carrier,
                                              tracking_number = tracking_number)
        self.process_response(self.send_message(gmodel.deliver_order_t(
            google_order_number = order_id,
            tracking_data = tracking,
            send_email = send_email or None
            )))

    def is_of_class(self, doc, cls):
        return doc.__class__ == cls

    MESSAGE_HANDLERS = {
        gmodel.new_order_notification_t:            'on_new_order',
        gmodel.order_state_change_notification_t:   'on_order_state_change',
        gmodel.authorization_amount_notification_t: 'on_authorization_amount',
        gmodel.risk_information_notification_t:     'on_risk_information',
        gmodel.charge_amount_notification_t:        'on_charge_amount',
        gmodel.refund_amount_notification_t:        'on_refund_amount',
        gmodel.chargeback_amount_notification_t:    'on_chargeback_amount',
        # Message(s) that we can't possibly recieve. Handle it anyway.
        gmodel.checkout_redirect_t:                 'on_checkout_redirect',
        }
    def recieve(self, input_xml):
        input = gxml.Document.fromxml(input_xml)
        on_handler = None
        if self.MESSAGE_HANDLERS.has_key(input.__class__):
            handler = self.MESSAGE_HANDLERS[input.__class__]
            on_handler = self.__class__.__dict__[handler]
            res = on_handler(self, input, input.google_order_number)
        else:
            res = 'Method for %s is not implemented yet' % (input.__class__,)
        return str(res)

    # Google sends a new order notification when a buyer places an order through Google Checkout.
    # Before shipping the items in an order, you should wait until you have also received
    # the risk information notification for that order as well as
    # the order state change notification informing you that the order's financial state
    # has been updated to CHARGEABLE.
    def on_new_order(self, notification, order_id):
        return 'on_new_order'
    def on_order_state_change(self, notification, order_id):
        return 'on_order_state_change'
    def on_authorization_amount(self, notification, order_id):
        return 'on_authorization_amount'
    # Google Checkout sends a risk information notification to provide financial information
    # that helps you to ensure that an order is not fraudulent.
    def on_risk_information(self, notification, order_id):
        return 'on_risk_information'
    def on_charge_amount(self, notification, order_id):
        return 'on_charge_amount'
    def on_refund_amount(self, notification, order_id):
        return 'on_refund_amount'
    def on_chargeback_amount(self, notification, order_id):
        return 'on_chargeback_amount'
    def on_checkout_redirect(self, notification, order_id):
        raise Exception('We should not recieve this method... Please report this bug.')
    def on_failed_recieve(self, input_xml, error_message):
        pass

class html_order:
    cart = None
    signature = None
    url = None
    button = None
    xml = None

if __name__ == '__main__':
    gc = Controller(vendor_id='your_google_sandbox_vendor_id',
                    merchant_key='your_google_merchant_key',
                    is_sandbox=True)
    order = create_order()
    html = gc.prepare_order(order)
    
    print "Input: %s" % (html.xml)
    print "--------------------"
    print gc.recieve(html.xml)

