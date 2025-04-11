
import os
from twilio.rest import Client

# Find your Account SID and Auth Token at twilio.com/console
# and set the environment variables. See http://twil.io/secure
account_sid = 'ACd8ee8e35154d0be246f580316e67e084'
auth_token = 'a967bbbc38c815950283f1b074a8f4ae'
client = Client(account_sid, auth_token)

message = client.messages.create(
    body="Join Earth's mightiest heroes. Like Kevin Bacon.",
    from_="+18457140497",
    to="+996551050858",
)

print(message.body)