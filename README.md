# Swick
Swick brings simplicity and efficiency to the dining experience. 
It serves as an alternative to traditional menus and expensive tablet systems.
By scanning a QR code at a table, the customer can browse the menu, order, and pay straight from the app.
Servers receive orders on their app, and have views of orders to cook and to send.
Restaurant owners can login to their dashboard to edit restaurant information, update their menu and view orders.

[Video demo on YouTube](https://youtu.be/IzwRwoeHSOk)

## Restaurant dashboard & backend
[Restaurant dashboard link](http://swickapp.herokuapp.com)
### Features
* Create an account
* View menu
* Add and update meals with customizations and price additions
* View current and past orders
* Manage servers
* View and update account information
### Technologies used
* Python
* Django
* Django REST Framework
* PostgreSQL
* Heroku
* Amazon S3
* Stripe
* HTML/CSS/JavaScript
* Bootstrap
* jQuery

## Customer App
[Github link](https://github.com/seanlu99/SwickCustomerIOS)
### Features
* Login through Facebook
* Browse restaurants and menus
* Scan QR code to link to restaurant and table
* Add and customize meals
* Search for restaurants, categories and meals
* Pay through Stripe
* View current and past orders
### Technologies used
* Swift
* Alamofire
* SwiftyJSON
* Facebook Login SDK
* Stripe

## Server App
[Github link](https://github.com/seanlu99/SwickServerIOS)
### Features
* Login through Facebook
* View orders to cook
* View orders to send
* View past orders
### Technologies used
Same as Customer App
