## Instructions on running application
1. Setup Firestore Database and Firebase Authentication at https://console.firebase.google.com/
2. Go to Project Settings in the Firebase Console and note down your web api key
3. Go to Service Accounts in settings and click generate new private key which will download a json file
4. Additionally, you will need to setup notifications via your gmail
5. Ensure your account has 2 factor authentication enabled
6. Visit https://myaccount.google.com/apppasswords and generate a password. Note this down
7. Run `docker build -t deliverable3 .`
8. Finally, run the following:
```
docker run -p 5001:5000 -e SENDER_EMAIL="<insert gmail here>" -e SENDER_PASSWORD="<insert generated password here>" -e AUTH_KEY="<insert web api key here>" -v <complete path to json file here>:/app/flask-tms/firebase-adminsdk.json deliverable3
```
9. Visit http://127.0.0.1:5001/