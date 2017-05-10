# Raspberry installation

1. Download repo, create virtualenv and install dependencies
2. Initialize the database with the lines you want. Eg:
    python manage.py init 192
    python manage.py init 169
    python manage.py init 110
3. Add the following to `/etc/rc.local`:
    su - pi -c "screen -dm -S tracker192 ~/stm-tracker-start-up.sh 192"
    su - pi -c "screen -dm -S tracker169 ~/stm-tracker-start-up.sh 169"
    su - pi -c "screen -dm -S tracker110 ~/stm-tracker-start-up.sh 110"
4. Create `~/stm-tracker-start-up.sh` like this:
    #!/bin/bash

    cd ~/stm-tracker/tracker
    source ../.env/bin/activate
    python manage.py track $1
