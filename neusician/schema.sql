PRAGMA foreign_keys=ON;

CREATE TABLE "user" (
    ROWID integer primary key,

    name CHAR NOT NULL,
        -- Username, to be sanity-checked at an upper level of
        -- validation.

    password VARCHAR NOT NULL,
        -- Make sure it is salted and hashed at an upper level.

    last_password_match DATETIME,
        -- Expected to be set before an authentication-demanding
        -- request is executed. When older than an hour, the user
        -- looses its worker reservation to whom demands next.

    expires_not_before DATETIME,
        -- There can be more users than workers available, so users
        -- will need to wait until one is free. Challenged patience,
        -- however, is rewarded with accordingly more expires_not_before
        -- time automatically when they finally do get a free worker, so
        -- it is reserved for them longer.
        --
        -- expires_not_before in the range of 0 <= x <= 1h from now, which
        -- is the default, does not give an advantage to one user over
        -- another. Those users are therefore equal among themselves.
        -- Users with more can wrest the worker from a randomly selected
        -- user with less expires_not_before time.
        --
        -- Technically, providers could boost their own, their friends'
        -- or paying users' expires_not_before time. They should ponder
        -- about moral considerations of this. But must Neusician be
        -- fairer than society out there? Giving anonymous users
        -- a share of your resources to make scripted music, to get
        -- an impression of how it works, should be regarded as an
        -- act of kindness, to be revoked or restricted at any
        -- time for whatever reason.

    needs_worker_since DATETIME,
        -- If a user looses its reserved worker to another with higher
        -- rank, they may still not find a free worker when needed.
        -- The longer they wait, the higher the rank in the queue of
        -- users waiting for a free worker or a worker reserved for an
        -- expired user or a user who has not made a request for an hour.

    tried_times INT DEFAULT 0,
        -- Set when there is still no free worker available for the user.
        -- Used as a means to rank them higher on the waiting queue when
        -- the interval between tries grows.
        -- Multiple tries within a minute are counted as one to prevent
        -- smart users from gaining rank boosts by trying too often and
        -- then taking a final deep breath and practice a little bit of
        -- patience with a big relative effect.

    given_resources INT NOT NULL,
        -- Second control besides expires_not_before to privilege users,
        -- and to foster fantasy of omnipotence ;). However, it is only
        -- the total_samples_max component of SOMPYLER_LIMITS environment
        -- variable, and is only respected when SOMPYLER_LIMITS does not
        -- define it. So, it is just meant a fallback, really.
        --
        -- SOMPYLER_LIMITS, with any being reached and exceeded, will cause
        -- Sompyler to stop functioning and to raise an ExceededLimitsError.
        -- In case of total_samples_max specifically, the reserved worker
        -- process cannot be used any more. The user needs to let it
        -- expire and reassigned to someone else, so they can wait to get
        -- assigned a fresh one. 

    constraint unique_username UNIQUE(name)
);

CREATE TABLE worker (
    id integer primary key,

    userid INT DEFAULT NULL REFERENCES user(ROWID) ON DELETE SET NULL,
        -- NULL if the worker is not reserved for a user.
        -- If you register a new worker, please make sure there is a
        -- directory with its id set up in $SOMPYLER_TEMP_DATA.

    used_resources INT DEFAULT 0,
        -- To be updated when a worker spit out an audio file

    taken_times INT,
        -- Used to calculate in connection with used_resources some
        -- bonus time to expires_not_only, so users can build upon
        -- sounds expensively produced and cached more likely.

    CONSTRAINT unique_owner UNIQUE(userid)
);

-- Cross product of workers and users with has_time (more or less)
CREATE VIEW stake AS
    SELECT NULL AS userid, NULL AS has_time, id AS assigned_to_worker
      FROM worker
      WHERE userid IS NULL
    UNION SELECT
        u.ROWID,
        (STRFTIME('%s', expires_not_before)
        -STRFTIME('%s', 'now'))/3600.0,
        w.id
      FROM "user" u
        LEFT OUTER JOIN worker w ON w.userid=u.ROWID
      WHERE expires_not_before < DATETIME('now')
    UNION SELECT
        u.ROWID,
        CASE WHEN STRFTIME(
            '%s', u.last_password_match
          ) > STRFTIME('%s', 'now', '-1 HOUR')
             THEN MAX(1, (
                 STRFTIME('%s', u.expires_not_before)
                 - STRFTIME('%s', 'now')
                 )/3600.0)-1
             ELSE NULL
        END,
        w.id
      FROM "user" u
        LEFT OUTER JOIN worker w ON w.userid=u.ROWID
      WHERE expires_not_before >= DATETIME('now')
    ;

-- Who is next, i.e. who waits and checks for availability 
-- of a worker in the most regular intervals.
CREATE VIEW waiting_users AS
    SELECT
      ROW_NUMBER() OVER(ORDER BY
      -- Good old SQLite3 has no square / exp op in the core?!
        STRFTIME('%s', last_password_match) - STRFTIME(
                 '%s', needs_worker_since
          )
      * STRFTIME('%s', last_password_match) - STRFTIME(
                 '%s', needs_worker_since
          )
      / MIN(0.001, ABS(
          ( STRFTIME('%s', 'now')
          - STRFTIME('%s', last_password_match)
          ) 
	- ( STRFTIME('%s', last_password_match)
          - STRFTIME('%s', needs_worker_since)
          ) / tried_times
        )) 
      ASC) AS wait_rank,
      ROWID AS userid
    FROM "user"
        WHERE userid NOT IN (SELECT IFNULL(userid, 0) FROM worker)
    ;

-- Rank-joining brokerage of waiting user and available_worker
CREATE VIEW available_workers AS SELECT * FROM worker;
CREATE TRIGGER assign_worker
    INSTEAD OF INSERT ON available_workers
BEGIN
UPDATE worker SET userid=NEW.userid, used_resources=0, taken_times=0
    WHERE id=(
      SELECT assigned_to_worker
      FROM (
	SELECT ROW_NUMBER() OVER(ORDER BY has_time ASC) AS time_rank,
	       * -- all other fields from original upper view
          FROM stake
         WHERE assigned_to_worker IS NOT NULL
      ) s1
        LEFT OUTER JOIN "user" u ON u.ROWID=s1.userid
        JOIN waiting_users wu ON s1.time_rank=wu.wait_rank
    WHERE  (s1.has_time < (
            SELECT has_time
            FROM stake s2 WHERE s2.userid=NEW.userid
        ) OR s1.has_time IS NULL)
      AND  wu.userid=NEW.userid -- Only match if waiting user has a rank
                -- high enough that there are as many workers idle or
                -- reserved for users now inactive (expires_not_before date
                -- in the past or last password match older than an hour).
    );
END;

-- If user sends an authenticated request to a server and the password
-- matches, the outer system must update user's last_password_match field
-- to the current time stamp. Then, we look for an available worker and
-- reserve it by setting userid field.
CREATE TRIGGER update_lpm_request_worker
    BEFORE UPDATE OF last_password_match ON "user"
    WHEN NEW.last_password_match > IFNULL(OLD.last_password_match, '')
BEGIN
    UPDATE "user"
      SET tried_times=tried_times+(
        -- Only count one try in a minute
        (STRFTIME('%s', NEW.last_password_match)
          - IFNULL(STRFTIME('%s', OLD.last_password_match), 0)
        ) > 59),
        needs_worker_since=IFNULL(needs_worker_since, DATETIME('now'))
      WHERE ROWID=OLD.ROWID;
    INSERT OR IGNORE INTO available_workers (userid) VALUES(OLD.ROWID);
END;

-- If we could reserve a worker, we reset some user fields accordingly.
-- If a user had got their worker wrested by some idiot with an
-- expires_not_before > now + 1 hour (i.e. the provider or a user
-- privileged by the provider notwithstanding all moral considerations),
-- their patience and forgiveness would be compensated with additional
-- reservation time up to two hours, depending on how long you have waited.
CREATE TRIGGER resets_on_successful_worker_assignment
    AFTER UPDATE OF last_password_match ON "user"
    WHEN OLD.ROWID IN (SELECT userid FROM worker)
BEGIN
    UPDATE "user"
       SET tried_times=0,
           expires_not_before=IFNULL(
             DATETIME(
               'now', '1 HOUR', MIN(7200,
                 STRFTIME('%s', 'now') - STRFTIME(
                  '%s', OLD.needs_worker_since
                 )) || ' SECONDS'),
             OLD.expires_not_before
           ),
           needs_worker_since=NULL
     WHERE ROWID=OLD.ROWID;

    -- When logging in at least 3 hours later and you have still your
    -- worker, reset your used resources so you get full quota back.
    UPDATE worker
       SET used_resources=0
     WHERE userid=OLD.ROWID
       AND DATETIME(OLD.last_password_match, '3 HOURS')
         < DATETIME('now');

END;

-- When a worker finished, outer system must increase used resources
-- to properly observe the total_samples_max limit in a next run.
-- Plus, the expires_not_before is extended to reduce the risk of
-- an expiration too soon that they have not time enough to rehear the
-- result and apply small corrections.
CREATE TRIGGER update_worker
    AFTER UPDATE ON worker
    WHEN NEW.used_resources > OLD.used_resources
-- This trigger grants the user some more time to re-use
-- samples that have been generated using time and cpu resources.
BEGIN
    UPDATE "user" SET expires_not_before=MAX(
       expires_not_before,
       DATETIME('now',
       CAST(MIN(1,
           ( NEW.used_resources - OLD.used_resources )
           * NEW.taken_times
           / NEW.used_resources
       ) * 3600 AS INT) || ' SECONDS'
       )
    ) WHERE ROWID=OLD.userid;

    -- We can probably do some housekeeping here. Drop users having
    -- been expired or whose last password for more than three hours.
    DELETE FROM "user"
        WHERE MAX(IFNULL(last_password_match, 0), expires_not_before)
        < DATETIME('now', '-12 HOURS')
    ;
END;

CREATE TRIGGER set_expiration_date
    AFTER INSERT ON "user"
    WHEN NEW.expires_not_before IS NULL
BEGIN
    UPDATE "user" SET expires_not_before=DATETIME('now', '1 HOUR')
        WHERE ROWID=NEW.ROWID;
END;
