delete from "user"
	where last_password_match < datetime('now', '-1 HOUR')
	  and expires_not_before < datetime('now')
    ;

update worker set used_resources=0
	where userid in (
	    select ROWID
	      from "user"
	     where last_password_match < datetime('now', '-1 HOUR')
	       and expires_not_before > datetime('now', '1 HOUR')
	)
    ;
