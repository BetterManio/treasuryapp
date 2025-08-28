The instructions to run this have slightly changed with the restructuring.

There is still the optional venv creation followed by pip install -r requirements.txt

Then 

export FLASK_APP=app

flask run

To run the app.

Unittests have been added and can be run with 

python3 -m unittest

The logic within the app has remained the same but the app itself has been restructured into modules with an app factory and blueprint format.

For this app we have three modules: main, orders, and yields. Besides main, which just has routes, each module has routes, models, and utils for helper functions. In future would have Forms for Order module
