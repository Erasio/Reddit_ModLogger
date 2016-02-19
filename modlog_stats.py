#!/usr/local/bin/python3.4

import praw
import time as sleep
import warnings
from datetime import datetime, date, time
import mysql_handler as db

warnings.simplefilter("ignore", ResourceWarning)

mod_actions = {}

def collect_modlog_stats(r, subreddit, time_limit = None):
    if time_limit:
        limit = datetime.combine(datetime.fromtimestamp(time_limit), time())
        epoch_limit = int (limit.strftime("%s"))

    current_day = datetime.combine(date.today(), time())
    epoch_current_day = int (current_day.strftime("%s"))

    for log_entry in r.get_mod_log(subreddit, limit=None):
        if time_limit:
            if log_entry.created_utc <= epoch_limit:
                print("Collection limit reached")
                break
        beginning_of_the_day = datetime.combine(datetime.fromtimestamp(log_entry.created_utc), time())
        epoch_beginning_of_the_day = int (beginning_of_the_day.strftime("%s"))

        if not epoch_beginning_of_the_day == epoch_current_day:
            if epoch_beginning_of_the_day > epoch_current_day:
                continue
            else:
                result = save_modlog(epoch_current_day, subreddit)
                if result == 0:
                    break
                epoch_current_day = epoch_beginning_of_the_day
                sleep.sleep(5)

        print(epoch_beginning_of_the_day)

        collect_log_entry(log_entry, epoch_beginning_of_the_day)


def save_modlog(current_day, subreddit):
    global mod_actions

    if not current_day == int (datetime.combine(date.today(), time()).strftime("%s")):

        print("Saving modlog for the day " + str(current_day))
    
        for mod in mod_actions[current_day]:
            for action in mod_actions[current_day][mod]:
                if not action == "reasons":
                    result = db.insert_modlog(current_day, mod, action, mod_actions[current_day][mod][action], subreddit)
                    if result == 0:
                        return 0
    
        if "AutoModerator" in mod_actions[current_day]:
            for reason in mod_actions[current_day]["AutoModerator"]["reasons"]:
                db.insert_automod(current_day, reason, mod_actions[current_day]["AutoModerator"]["reasons"][reason], subreddit)
    
        del mod_actions[current_day]
        return 1
    return 0


def collect_log_entry(log_entry, day):
    global mod_actions

    if day in mod_actions:
        check_mod(log_entry, day)
    else:
        mod_actions[day] = {}
        check_mod(log_entry, day)



def check_mod(log_entry, day):
    global mod_actions

    if log_entry.mod == "AutoModerator":
        if not "AutoModerator" in mod_actions[day]:
            mod_actions[day][log_entry.mod] = {}
            mod_actions[day][log_entry.mod]["reasons"] = {}

    if log_entry.mod in mod_actions[day]:
        insert_log(log_entry, day)
    else:
        mod_actions[day][log_entry.mod] = {}
        insert_log(log_entry, day)


def insert_log(log_entry, day):
    if log_entry.action.lower() in mod_actions[day][log_entry.mod]:
        mod_actions[day][log_entry.mod][log_entry.action.lower()] += 1
    else:
        mod_actions[day][log_entry.mod][log_entry.action.lower()] = 1

    if log_entry.mod == "AutoModerator":
        if log_entry.details:
            spearators = [
                ",",
                ":",
                "-"
            ]

            detail = log_entry.details
            for sparator in spearators:
                detail = detail.split(sparator)
                detail = detail[0]

            if detail in mod_actions[day][log_entry.mod]["reasons"]:
                mod_actions[day][log_entry.mod]["reasons"][detail] += 1
            else:
                mod_actions[day][log_entry.mod]["reasons"][detail] = 1
