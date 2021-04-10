import os, subprocess, re
from glob import glob
import sqlite3

con = None

STD_RESOURCES = 10**9

TMPDIR="/var/tmp/sompyler/data"

class NoWorkersAvailableError(RuntimeError):
    pass

def register_worker(worker_id):

    wdir = os.path.join(TMPDIR, '{:02d}'.format(int(worker_id)))
    if not (os.path.isdir(wdir) and os.access(wdir, os.X_OK|os.W_OK)):
        raise FileNotFoundError(
                f"worker directory {path} not existent and writable"
            )

    c = con.cursor()
    c.execute("INSERT OR IGNORE INTO worker(id) VALUES (?)", (worker_id,))


def init_db(path):
    global con
    if os.path.getsize(path):
        print(f"Just establishing connection with "
               "initialized database {path}. "
            )
        con = sqlite3.connect(path)
        return
    else:
        con = sqlite3.connect(path)

    c = con.cursor()
    c.executescript(open("schema.sql").read())

    wid = 0
    for wdir in glob(os.path.join(TMPDIR, '[0-9][0-9]')):
        wid = wdir.rsplit('/', 1)[1]
        try:
            register_worker(wid)
        except FileNotFoundError as e:
            print(e)

    con.commit()


def register_user(name, password):

    c = con.cursor()
    c.execute("INSERT INTO user(name, password, given_resources)"
              "VALUES (?, ?, ?);", (name, password, STD_RESOURCES)
        )

    con.commit()

def get_hashed_password_of_user(name):

    c = con.cursor()
    try: return next(c.execute(
            "SELECT password FROM user WHERE name = ?", (name,)
        ))[0]
    except StopIteration:
        return None


def user_is_authenticated(name):

    c = con.cursor()
    c.execute("UPDATE user SET last_password_match=DATETIME('now')"
              " WHERE name=?", (name,)
        )
    con.commit()


def worker_directory_of_user(name, *path):

    c = con.cursor()
    try:
        worker_id = next(c.execute("""
            SELECT id
              FROM worker w
              JOIN user u ON w.userid=u.ROWID
             WHERE u.name=?
            """,
            (name,)
        ))[0]
    except StopIteration as e:
        rank = next(c.execute("""
            SELECT wait_rank
              FROM waiting_users
              JOIN user u ON w.userid=u.ROWID
             WHERE u.name=?
            """,
            (name,)
        ))[0]
        raise NoWorkersAvailableError(
                f"{rank-1} users preceed in queue".format(rank)
            ) from e

    return os.path.join(TMPDIR, '{:02d}'.format(worker_id), *path)


def initialize_sompyler(user, score):
    c = con.cursor()
    userid, resources = next(c.execute("""
        SELECT u.ROWID, given_resources - used_resources
          FROM user u
          JOIN worker w ON u.ROWID=w.userid
         WHERE u.name=?
        """, (user,)
    ))
    os.environ["SOMPYLER_LIMITS"] = os.environ["SOMPYLER_LIMITS"].replace(
        "::", f":{resources}:"
    )

    with open(worker_directory_of_user(user, "score"), "w") as score_fh:
        c.execute(
            "UPDATE worker SET taken_times=taken_times+1 WHERE userid=?",
            (userid,)
        )
        print(score, file=score_fh)
        con.commit()


def get_status(user):

    res = subprocess.run(
      [ "bash", "single-sompyler-procman.sh",
        worker_directory_of_user(user), user
      ], capture_output=True, check=True
    )

    notes, status, errors = res.stdout.decode("utf-8").split("---\n")

    progress, *status = status.split("\n")
    current, total, reused_percent, remtime, res = progress.split()

    if status:
        m = re.search(r"\S+\.\w+", status[0])
        if m:
            status = { 'file_accomplished': m.group(0) }
        else:
            status = { 'remaining_time': status[0] or remtime }

    if 'file_accomplished' in status \
            or status.get('remaining_time').startswith("FAIL"):
        c = con.cursor()
        c.execute("""
            UPDATE worker SET used_resources=used_resources+?
            WHERE userid=(SELECT ROWID FROM user WHERE name=?)
        """,
            (res, user)
        )
        con.commit()

    return {
        'notes_log': notes,
        'currently_rendered_notes': int(current),
        'total_notes_to_render': int(total),
        'reused_percent': float(reused_percent),
        'total_samples_calculated': int(res),
        **status,
        'errors': errors,
    }
