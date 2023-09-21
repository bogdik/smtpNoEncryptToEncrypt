from aiosmtpd.smtp import AuthResult, LoginPassword
from aiosmtpd.controller import Controller
import smtplib
import warnings
warnings.filterwarnings("ignore")

auth_db = {}

class LocalServerHandler:
    def __init__(self, host, port=0, auth=None, proxy_auth=False, use_ssl=False, starttls=False):
        self._host = host
        self._port = port
        self._proxy_auth=proxy_auth
        self._auth = auth or {}
        self._auth_user = self._auth.get('username')
        self._auth_password = self._auth.get('password')
        self._use_ssl = use_ssl
        self._starttls = starttls

    async def handle_DATA(self, server, session, envelope):
        refused = {}
        try:
            refused = self._send_remote(envelope, session)
        except smtplib.SMTPRecipientsRefused as e:
            return "553 Recipients refused {}".format(' '.join(refused.keys()))
        except smtplib.SMTPResponseException as e:
            return "{} {}".format(e.smtp_code, e.smtp_error)
        else:
            if refused:
                print('Recipients refused: %s', self.refused)
            return '250 OK'

    def _send_remote(self, envelope, session):
        self.refused = {}
        try:
            if self._use_ssl:
                s = smtplib.SMTP_SSL()
                s.connect(self._host, self._port)
            else:
                s = smtplib.SMTP(self._host, self._port)

            if self._starttls:
                s.starttls()
                s.ehlo()
            if self._auth_user and self._auth_password and not self._proxy_auth:
                s.login(self._auth_user, self._auth_password)
            elif self._proxy_auth:
                global auth_db
                s.login(auth_db[session]['username'], auth_db[session]['password'])
            try:
                self.refused = s.sendmail(
                    envelope.mail_from,
                    envelope.rcpt_tos,
                    envelope.original_content
                )
            finally:
                s.quit()
        except (OSError, smtplib.SMTPException) as e:
            print('got %s', e.__class__)
            # All recipients were refused. If the exception had an associated
            # error code, use it.  Otherwise, fake it with a SMTP 554 status code.
            errcode = getattr(e, 'smtp_code', 554)
            errmsg = getattr(e, 'smtp_error', e.__class__)
            raise smtplib.SMTPResponseException(errcode, errmsg.decode())

def authenticator_func(server, session, envelope, mechanism, auth_data):
    global auth_db
    auth_db[session]={'username':auth_data.login.decode(),'password':auth_data.password.decode()}
    return AuthResult(success=True)

if __name__ == '__main__':
        local_server_host='localhost'
        local_server_port = 25
        local_use_auth = True
        local_use_tls = False
        remote_server_host= 'smtp.youremoteserver.com'
        remote_username = ''
        remote_password = ''
        remote_server_port = 587
        remote_use_auth=True
        proxy_auth=True
        if proxy_auth and not local_use_auth:
            print('If use ProxyAuth need use Loacal Auth')
            exit()
        if remote_use_auth and not proxy_auth:
            auth = {
                'username': remote_username,
                'password': remote_password
            }
        else:
            auth = None
        remote_use_ssl = False
        remote_starttls = True

        controller = Controller(
                handler = LocalServerHandler(
                    host=remote_server_host,
                    port=remote_server_port,
                    auth=auth,
                    proxy_auth=proxy_auth,
                    use_ssl=remote_use_ssl,
                    starttls=remote_starttls,
                ),
                hostname=local_server_host,
                port=local_server_port,
                authenticator=authenticator_func,  # i.e., the name of your authenticator function
                auth_require_tls=local_use_tls,
                auth_required=local_use_auth,  # Depending on your needs
        )
        controller.start()
        # Wait for the user to press Return.
        input('SMTP server running. Press Return to stop server and exit.')
        controller.stop()
