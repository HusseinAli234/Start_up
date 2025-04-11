from twilio.rest import Client
account_sid = 'ACd8ee8e35154d0be246f580316e67e084'
auth_token = 'a967bbbc38c815950283f1b074a8f4ae'
client = Client(account_sid, auth_token)
message = client.messages.create(
  messaging_service_sid='MG28a4fdcf2905ff9ebc81dbe4cfcb22f4',
  body='Ahoy 👋',
  to='+996553333829'
)
print(message.sid)