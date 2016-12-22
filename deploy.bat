rem delete sqlite3 database
del db.sqlite3

rem delete migration files
del tool_share\migrations\0*.py

rem make migrations
python manage.py makemigrations

rem generate database
python manage.py migrate

rem removing all files and folders inside staticroot folder
del staticroot\*.* /s /Q

rem collect static files
python manage.py collectstatic --noinput

rem run the tool_share/management/command/deploy.py script to auto generate sample data
python manage.py deploy

rem start the server
python manage.py runserver