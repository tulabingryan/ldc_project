
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time


def send_email(sender='ldc.email0@gmail.com', password='ArdmoreECE987', msg_subect='IP', message=' ', receiver='ldc.email0@gmail.com'):
    ''' Send email message '''
    host = sender.split('@')[1]
    if host=='gmail.com':
        smtp_ssl_host = 'smtp.gmail.com'
    elif host=='yahoo.com':
        smtp_ssl_host = 'smtp.mail.yahoo.com'
    
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = msg_subect
    msg.attach(MIMEText(message, 'plain'))

    mail = smtplib.SMTP(smtp_ssl_host, 587)
    mail.starttls()
    mail.login(sender, password)
    mail.sendmail(sender, receiver, msg.as_string())
    mail.quit()


###---test send_email -----------------------------------
# send_email(sender='ldc.email0@gmail.com', 
#   password='ArdmoreECE987', 
#   msg_subect='IP', 
#   message='Test message...', 
#   receiver='ldc.email0@gmail.com')

###----------------------------------------------------



from urllib.request import urlopen
import json

def get_public_ip():
    ''' Get public IP adress of the router'''

    req = 'http://ip-api.com/json'
    try:
        response = urlopen(req)
        respData = response.read()
        respData = respData.decode("utf-8")
        response = json.loads(respData)
        public_ip = response['query']
    
    except Exception as e:
        print(e)
    
    print('external ip address: {}'.format(public_ip))
    return public_ip

###---test get_public_ip---
# ip = get_public_ip()
###------------------


import socket

def get_local_ip():
    # get local ip address
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            break
        except Exception as e:
            print("Error in get_local_ip: ", e)
            pass
    return local_ip



def send_ip():
    ''' Send latest public IP Address'''
    ip = get_public_ip()
    ID = get_local_ip()
    send_email(sender='ldc.email0@gmail.com', 
            password='ArdmoreECE987', 
            msg_subect='IP', # + ID, 
            message= '\npublic ip: ' + str(ip) + '\nlocal ip: ' + str(ID),
            receiver='ldc.email0@gmail.com')
    print('Latest publice IP address sent...')
    return


###---test send_ip-----------------
#send_ip()
###-------------------------------








if __name__=='__main__':
    
    last_ip = get_public_ip()
    send_ip()
    while True:
        try:
            ip = get_public_ip()
            if ip==last_ip:
                print('IP address has not changed... \nSleeping for 30s...')
                time.sleep(30)

            else:
                send_ip()
                last_ip = ip
                print('New public IP address recorded...')

        except Exception as e:
            print(e)

