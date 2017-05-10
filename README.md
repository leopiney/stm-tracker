# Raspberry installation

1. Download repo, create virtualenv and install dependencies
2. Add the following to `/etc/rc.local`:
    su - pi -c "screen -dm -S tracker ~/stm-tracker-start-up.sh 192"
    su - pi -c "screen -dm -S tracker ~/stm-tracker-start-up.sh 169"
    su - pi -c "screen -dm -S tracker ~/stm-tracker-start-up.sh 110"
3. Create `~/stm-tracker-start-up.sh` like this:
    #!/bin/bash

    cd ~/stm-tracker/tracker
    source ../.env/bin/activate
    python manage.py $1
