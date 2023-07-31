#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import datetime, warnings


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feed_aggregator.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    INITIAL_ARGV = sys.argv.copy()

    if os.environ.get('RUN_MAIN', 'false') == 'false':
        print(f'Django Server was started at: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")}')
        warnings.filterwarnings("ignore", message="Using slow pure-python SequenceMatcher. Install python-Levenshtein to remove this warning")

        # Make data model migrations
        sys.argv = [INITIAL_ARGV[0], 'makemigrations']
        main()

        # Apply data model migrations
        sys.argv = [INITIAL_ARGV[0], 'migrate']
        main()

        from django.contrib.auth.models import User
        from feeds.models import Feed

        # Load initial feeds
        if len(Feed.objects.all()) == 0:
            sys.argv = [INITIAL_ARGV[0], 'add_default_feeds']
            main()

        # Create Admin
        if len(User.objects.filter(username='admin')) == 0:
            print('Create super user "admin"')
            User.objects.create_superuser('admin', '', 'Sven1006')

    else:
        print('Django auto-reloader process executes second instance of django. Please turn-off for production usage by executing: "python manage.py runserver --noreload"')

    # Run server
    sys.argv = INITIAL_ARGV
    main()
