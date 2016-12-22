Steps to run Tool Share server on the local machine

1. Checkout the source code to your machine, if you have not already done that.
2. From the project's root directory, run deploy.bat batch file. This will
	> Delete db.sqlite3 and any migrations file in your repository
	> Run the makemigrations django command
	> Create the local database by executing the migrate command
	> Run the deploy.py command script to generate sample data for the application
	> Start the Django server by running the runserver command
3. Navigate to http://localhost:8000/ from your browser

Sample credentials
	zone: 12345
	pratham@mp.com	
	palash@mp.com
	
	zone: 54321
	michelle@mp.com
	jadder@mp.com
	satyajit@mp.com

	super user:
	admin@mp.com
	
Sample passwords (for all)
	Hol1Hol1