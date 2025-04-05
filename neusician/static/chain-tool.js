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
         lane_ids = new Array(cols * rows + 1);
         table.data("laneids", lane_ids);
         table.data("touched", touched);
	 table.data("cols", cols)
         return;
    }

    var touched_lanes = touched.sorted_lanes(),
        min_lane_id = touched_lanes[0];
    
    console.log(`touched_lanes = ${touched_lanes.join(", ")}`);
    if ( min_lane_id > spare_lane_id ) {
        spare_lane_id = min_lane_id;
	console.log(`New spare_lane_id = ${spare_lane_id}`)
    }

    const i_left = -1;
    const i_dgnw = -1 - cols;
    const i_top = -cols;
    const i_dgne = +1 - cols;
    const i_right = +1;
    const i_dgse = +1 + cols;
    const i_bottom = +cols;
    const i_dgsw = -1 + cols;
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
        var leftroom = Boolean(linc % cols);
        var toproom = linc+1 > cols;
        var rightroom = Boolean((linc+1) % cols);
        var bottomroom = Math.ceil((linc+1) / cols) < rows;

	let l_left = linc + i_left;
	if ( l_left < 0 ) l_left = -1;
        let strl = touched.is( lane_ids[l_left] );

	let l_top = linc + i_top;
	if ( l_top < 0 ) l_top = -1;
        let stru = touched.is( lane_ids[l_top] );
	
	let l_right = linc + i_right;
	if ( l_right >= lane_ids.length ) l_right = -1;
        let strr = touched.is( lane_ids[l_right] );
	
	let l_bottom = linc + i_bottom;
	if ( l_bottom >= lane_ids.length ) l_bottom = -1;
        let strd = touched.is( lane_ids[l_bottom] );
	
	let l_dgnw = linc + i_dgnw;
	if ( l_dgnw < 0 ) l_dgnw = -1
        let dgnw = touched.is( lane_ids[l_dgnw] );
	
	let l_dgne = linc + i_dgne;
	if ( l_dgne < 0 ) l_dgne = -1;
        let dgne = touched.is( lane_ids[l_dgne] );
	
	let l_dgse = linc + i_dgse;
	if ( l_dgse >= lane_ids.length ) l_dgse = -1;
        let dgse = touched.is( lane_ids[l_dgse] );
	
	let l_dgsw = linc + i_dgse;
	if ( l_dgsw >= lane_ids.length ) l_dgsw = -1;
        let dgsw = touched.is( lane_ids[l_dgsw] );

        if ( new_state == true ) {
            if ( $(this).hasClass("marked") ) {
		console.log(`${linc}: L${leftroom} T${toproom} R${rightroom} B${bottomroom}`);
                $(this).addClass("active-lane");
            }
            else {
		if (touched_lanes.includes(lane_ids[linc]))
		    $(this).addClass("active-lane");
		else
                    $(this).removeClass("active-lane");
                return;
            }

            if ( leftroom && (dgsw || strl || dgnw) ) {
                if (strl) {
                    tds.eq(l_left).addClass("merge-right");
                    $(this).addClass("merge-left");
		    indicator += 1;
                }
                else {
                    if ( dgsw ) {
			tds.eq(l_dgsw).addClass("merge-right");
			indicator += 2;
		    }
                    if ( dgnw ) {
		    	tds.eq(l_dgnw).addClass("merge-right");
			indicator += 4;
		    }
                }
            }

            if ( toproom && (dgnw || stru || dgne) ) {
                if (stru) {
                    tds.eq(l_top).addClass("merge-bottom");
                    $(this).addClass("merge-top");
		    indicator += 8;
                }
                else {
                    if ( dgnw ) {
		    	tds.eq(l_dgnw).addClass("merge-bottom");
			indicator += 16;
		    }
                    if ( dgne ) {
		    	tds.eq(l_dgne).addClass("merge-bottom");
			indicator += 32;
		    }
                }
            }

            if ( rightroom && (dgne || strr || dgse) ) {
                if (strr) {
                    tds.eq(l_right).addClass("merge-left");
                    $(this).addClass("merge-right");
		    indicator += 64;
                }
                else {
                    if ( dgnw ) {
		    	tds.eq(l_dgne).addClass("merge-left");
			indicator += 128;
		    }
                    if ( dgse ) {
		    	tds.eq(l_dgse).addClass("merge-left");
			indicator += 256;
		    }
                }
            }

            if ( bottomroom && (dgse || strd || dgsw) ) {
                if (strd) {
                    tds.eq(l_bottom).addClass("merge-top");
                    $(this).addClass("merge-bottom");
		    indicator += 512;
                }
                else {
                    if ( dgnw ) {
		    	tds.eq(l_dgnw).addClass("merge-top");
			indicator += 1024;
		    }
                    if ( dgsw ) {
		        tds.eq(l_dgsw).addClass("merge-top");
			indicator += 2048;
		    }
                }
            }

            console.log(`indicator: ${indicator}`);

        }

        else if ( new_state == false ) {
            if ( !$(this).hasClass("marked") ) return;
            if ( leftroom && lane_ids[l_left] != null )
                tds.eq(l_left).removeClass("merge-right");

            if ( leftroom && toproom && lane_ids[l_dgnw] != null ) {
               if ( lane_ids[l_left] == null)
                 tds.eq(l_dgnw).removeClass("merge-bottom");
               if (lane_ids[l_top] == null)
                 tds.eq(l_dgnw).removeClass("merge-right");
            }

            if ( toproom && lane_ids[l_top] != null )
                tds.eq(l_top).removeClass("merge-bottom");

            if ( toproom && rightroom && lane_ids[l_dgne] != null ) {
               if ( lane_ids[l_right] == null )
                 tds.eq(l_dgnw).removeClass("merge-bottom");
               if ( lane_ids[l_top] == null )
                 tds.eq(l_dgnw).removeClass("merge-left");
            }

            if ( rightroom && lane_ids[l_right] != null )
                tds.eq(l_right).removeClass("merge-left");

            if ( rightroom && bottomroom && lane_ids[l_dgse] != null ) {
               if ( lane_ids[l_right] == null )
                 tds.eq(l_dgse).removeClass("merge-top");
               if ( lane_ids[l_bottom] == null )
                 tds.eq(l_dgnw).removeClass("merge-left");
            }

            if ( bottomroom && lane_ids[l_bottom] != null )
                tds.eq(l_bottom).removeClass("merge-top");

            if ( bottomroom && leftroom && lane_ids[l_dgsw] != null ) {
               if ( lane_ids[l_left] == null )
                 tds.eq(l_dgse).removeClass("merge-top");
               if ( lane_ids[l_bottom] == null )
                 tds.eq(l_dgnw).removeClass("merge-right");
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
