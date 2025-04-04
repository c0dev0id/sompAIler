spare_lane_id = 0;
function Counter() {
    let cnt = {};

    this.up = function (name) {
        if (name in cnt)
            ++cnt[name];
        else cnt[name] = 1;
        return cnt[name];
    }

    this.down = function (name) {
        if (name in cnt && cnt[name])
            --cnt[name];
        return cnt[name];
    }

    this.reset = function (name) {
	if (name in cnt) cnt[name] = 0;
	return;
    }

    this.is = function (name) {
	if (name in cnt) return cnt[name] > 0;
	else return;
    }

    this.sorted_lanes = function () {
        return Object.keys(cnt).filter((n) => cnt[n] > 0).map((x) => parseInt(x)).toSorted();
    }
}

function change_state(table, new_state) {
    console.log("Change state to " + new_state);
    var table = table.find("tbody");
    var tds = table.find("td");
    var lane_ids = table.data("laneids");
    var touched = table.data("touched") || new Counter();
    var rows = table.children("tr");
    var cols = rows.eq(1).children("td").length;
    rows = rows.length - 1;
    if ( lane_ids == null ) {
         lane_ids = new Array(cols * rows);
         table.data("laneids", lane_ids);
         table.data("touched", touched);
	 table.data("cols", cols)
         return;
    }

    var min_lane_id = touched.sorted_lanes()[0];
    
    if ( min_lane_id > spare_lane_id ) {
        spare_lane_id = min_lane_id;
	console.log(`New spare_lane_id = ${spare_lane_id}`)
    }

    const i_left = -1;
    const i_dgnw = -1 - rows;
    const i_top = -rows;
    const i_dgne = +1 - rows
    const i_right = +1;
    const i_dgse = +1 + rows;
    const i_bottom = +rows;
    const i_dgsw = -1 + rows;
    table.children("tr").each(function (i) {
        i -= 1;
        $(this).children("td").each(function (j) {
             let linc = i * cols + j;
             if ( $(this).hasClass("marked") ) {
                 if (new_state) {
                     lane_ids[ linc ] = min_lane_id;
                     if ( $(this).is(":empty") ) {
			 $(this).append("<div>");
		     }
                 }
                 else {
                     lane_ids[ linc ] = null;
                     $(this).empty();
                 }
             }
        });
    });
    tds.each(function (linc) {
    	var indicator = 0;
        var leftroom = linc % cols;
        var toproom = linc+1 > cols;
        var rightroom = linc+1 % cols;
        var bottomroom = linc / cols - rows + 1 < rows;

        if ( new_state == true ) {
            if ( $(this).hasClass("marked") ) {
                $(this).addClass("active-lane");
            }
            else {
		if (lane_ids[linc] == min_lane_id)
		    $(this).addClass("active-lane");
		else
                    $(this).removeClass("active-lane");
                return;
            }

            let strl = touched.is( lane_ids[linc + i_left] );
            let stru = touched.is( lane_ids[linc + i_top] );
            let strr = touched.is( lane_ids[linc + i_right] );
            let strd = touched.is( lane_ids[linc + i_bottom] );
            let dgnw = touched.is( lane_ids[linc + i_dgnw] );
            let dgne = touched.is( lane_ids[linc + i_dgne] );
            let dgse = touched.is( lane_ids[linc + i_dgse] );
            let dgsw = touched.is( lane_ids[linc + i_dgsw] );

            if ( leftroom && (dgsw || strl || dgnw) ) {
                if (strl) {
                    tds.eq(linc + i_left).addClass("merge-right");
                    $(this).addClass("merge-left");
		    indicator += 1;
                }
                else {
                    if ( dgsw ) {
			tds.eq(linc + i_dgsw).addClass("merge-right");
			indicator += 2;
		    }
                    if ( dgnw ) {
		    	tds.eq(linc + i_dgnw).addClass("merge-right");
			indicator += 4;
		    }
                }
            }

            if ( toproom && (dgnw || stru || dgne) ) {
                if (stru) {
                    tds.eq(linc + i_top).addClass("merge-bottom");
                    $(this).addClass("merge-top");
		    indicator += 8;
                }
                else {
                    if ( dgnw ) {
		    	tds.eq(linc + i_dgnw).addClass("merge-bottom");
			indicator += 16;
		    }
                    if ( dgne ) {
		    	tds.eq(linc + i_dgne).addClass("merge-bottom");
			indicator += 32;
		    }
                }
            }

            if ( rightroom && (dgne || strr || dgse) ) {
                if (strr) {
                    tds.eq(linc + i_right).addClass("merge-left");
                    $(this).addClass("merge-right");
		    indicator += 64;
                }
                else {
                    if ( dgnw ) {
		    	tds.eq(linc + i_dgne).addClass("merge-left");
			indicator += 128;
		    }
                    if ( dgse ) {
		    	tds.eq(linc + i_dgse).addClass("merge-left");
			indicator += 256;
		    }
                }
            }

            if ( bottomroom && (dgse || strd || dgsw) ) {
                if (strd) {
                    tds.eq(linc + i_bottom).addClass("merge-top");
                    $(this).addClass("merge-bottom");
		    indicator += 512;
                }
                else {
                    if ( dgnw ) {
		    	tds.eq(linc + i_dgnw).addClass("merge-top");
			indicator += 1024;
		    }
                    if ( dgsw ) {
		        tds.eq(linc + i_dgsw).addClass("merge-top");
			indicator += 2048;
		    }
                }
            }

            console.log(`indicator: ${indicator}`);

        }

        else if ( new_state == false ) {
            if ( !$(this).hasClass("marked") ) return;
            if ( leftroom && lane_ids[linc + i_left] != null )
                tds.eq(linc + i_left).removeClass("merge-right");

            if ( leftroom && toproom && lane_ids[linc + i_dgnw] != null ) {
               if ( lane_ids[linc + i_left] == null)
                 tds.eq(linc + i_dgnw).removeClass("merge-bottom");
               if (lane_ids[linc + i_top] == null)
                 tds.eq(linc + i_dgnw).removeClass("merge-right");
            }

            if ( toproom && lane_ids[linc + i_top] != null )
                tds.eq(linc + i_top).removeClass("merge-bottom");

            if ( toproom && rightroom && lane_ids[linc + i_dgne] != null ) {
               if ( lane_ids[linc + i_right] == null )
                 tds.eq(linc + i_dgnw).removeClass("merge-bottom");
               if ( lane_ids[linc + i_top] == null )
                 tds.eq(linc + i_dgnw).removeClass("merge-left");
            }

            if ( rightroom && lane_ids[linc + i_right] != null )
                tds.eq(linc + i_right).removeClass("merge-left");

            if ( rightroom && bottomroom && lane_ids[linc + i_dgse] != null ) {
               if ( lane_ids[linc + i_right] == null )
                 tds.eq(linc + i_dgse).removeClass("merge-top");
               if ( lane_ids[linc + i_bottom] == null )
                 tds.eq(linc + i_dgnw).removeClass("merge-left");
            }

            if ( bottomroom && lane_ids[linc + i_bottom] != null )
                tds.eq(linc + i_bottom).removeClass("merge-top");

            if ( bottomroom && leftroom && lane_ids[linc + i_dgsw] != null ) {
               if ( lane_ids[linc + i_left] == null )
                 tds.eq(linc + i_dgse).removeClass("merge-top");
               if ( lane_ids[linc + i_bottom] == null )
                 tds.eq(linc + i_dgnw).removeClass("merge-right");
            }
        }

        $(this).removeClass("marked");

    });
    let old_value = lane_ids[min_lane_id];
    console.log(`${min_lane_id} / ${old_value} was the old value`);
    touched.reset(min_lane_id);
}

$(function () {
    change_state($("table"), null); /* init */
    $("td").on("click", function (e) {
        e.stopImmediatePropagation();
        $(this).toggleClass("marked");
        var tbody = $(this).closest("tbody");
	var index = tbody.data("cols") * ($(this).parent().index()-1) + $(this).index() - 1;
        var lane_id = tbody.data("laneids")[ index ] || spare_lane_id+1;
        var touched = tbody.data("touched")[ $(this).hasClass("marked") ? "up" : "down" ](lane_id);
        console.log(`Lane id ${lane_id} now marked ${touched} times.`);
        var x = $(this).closest("tr").children("td").index(this);
        tbody.find(".in-l").first().val(x);
        tbody.find(".in-r").first().val($(this).closest("tr").children().length - x - 2);
        var y = $(this).closest("tr").index() - 1;
        tbody.find(".in-u").first().val(y);
        tbody.find(".in-d").first().val($(this).closest("tbody").children().length - y - 2);
        
    });
    $("#adder").click(function (e) {
        e.preventDefault();
        change_state($(this).closest("table"), true);
    });
    $("#dropper").click(function (e) {
        e.preventDefault();
        change_state($(this).closest("table"), false);
    });
    $(".in-l").spinner();
    $(".in-r").spinner();
    $(".in-u").spinner();
    $(".in-d").spinner();
});
