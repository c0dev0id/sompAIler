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

function write_lines(table) {
    console.log("write lines");
    var lane_ids = table.find("tbody").data("laneids");
    var cols = table.find("tbody").data("cols");
    if (!lane_ids) return "null";
    var base = $("input[name=base]").val();
    var maxheight = $("input[name=rows]").val() - base;
    var lines = [], last = 0;
    var col = 0, row = -1;
    while ( true ) {
	if ( col % cols == 0 ) {
	    col = 0;
	    last = 0;
	    row++;
	}
	if ( lane_ids.length-1 == cols * row + col ) break;
	else if ( !col ) lines.push([0]);	
	current = lane_ids[ cols * row + col ] || 0;
	subarr = lines.at(-1);
	if ( current == last ) {
	    subarr[subarr.length-1] += current ? 1 : -1;
        }
	else {
	    subarr.push(current ? 1 : -1);
	    last = current;
	}
	col++;
    }
    lines.forEach(function (line, i) {
	var out = [];
        line.forEach(function (cur) {
	    if (cur == -1) {
		out.push(".");
	    }
	    else if (cur == -cols) {
		lines[i] = null;
		return;
	    }
	    else if (cur < 0 && cur > -cols) {
		out.push(`.${-cur}`);
	    }
	    else if (cur == 1) {
		out.push("o");
	    }
	    else if (cur == 2) {
		out.push("o_");
	    }
	    else if (cur == 3) {
		out.push("o__");
	    }
            else if (cur > 3) {
		out.push(`o_${cur-1}`);
            }
	});
	maxheight--;
	lines[i] &&= maxheight + " " + out.join("");
    });
    return "\n- " + lines.filter((el) => !!el).join("\n- "); 
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
    function is_touched (linc) {
        if ( linc < 0 || linc >= lane_ids.length ) linc = -1;
	return touched.is( lane_ids[linc] ) ? tds.eq(linc) : null;
    }
    tds.each(function (linc) {
    	var indicator = 0;
        var leftroom = Boolean(linc % cols);
        var toproom = linc+1 > cols;
        var rightroom = Boolean((linc+1) % cols);
        var bottomroom = Math.ceil((linc+1) / cols) < rows;

	let strl = is_touched(linc + i_left);
	let stru = is_touched(linc + i_top);
	let strr = is_touched(linc + i_right);
	let strd = is_touched(linc + i_bottom);
	
	let dgnw = is_touched(linc + i_dgnw);
	let dgne = is_touched(linc + i_dgne);
	let dgse = is_touched(linc + i_dgse);
	let dgsw = is_touched(linc + i_dgsw);

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
                    $(this).addClass("merge-left");
                    strl.addClass("merge-right str-right");
		    indicator += 1;
                }
                else {
                    if ( !stru && !strd ) $(this).addClass("merge-left");
                    if ( dgsw ) {
			dgsw.addClass("merge-right");
			indicator += 2;
		    }
                    if ( dgnw ) {
		    	dgnw.addClass("merge-right");
			indicator += 4;
		    }
                }
            }

            if ( toproom && (dgnw || stru || dgne) ) {
                if (stru) {
                    $(this).addClass("merge-top");
                    stru.addClass("merge-bottom str-bottom");
		    indicator += 8;
                }
                else {
                    if ( !strl && !strr ) $(this).addClass("merge-top");
                    if ( dgnw ) {
		    	dgnw.addClass("merge-bottom");
			indicator += 16;
		    }
                    if ( dgne ) {
		    	dgne.addClass("merge-bottom");
			indicator += 32;
		    }
                }
            }

            if ( rightroom && (dgne || strr || dgse) ) {
                if (strr) {
		    $(this).addClass("merge-right");
                    strr.addClass("merge-left str-left");
		    indicator += 64;
                }
                else {
                    if ( !stru && !strd ) $(this).addClass("merge-right");
                    if ( dgne ) {
		    	dgne.addClass("merge-left");
			indicator += 128;
		    }
                    if ( dgse ) {
		    	dgse.addClass("merge-left");
			indicator += 256;
		    }
                }
            }

            if ( bottomroom && (dgse || strd || dgsw) ) {
                if (strd) {
		    $(this).addClass("merge-bottom");
                    strd.addClass("merge-top str-top");
		    indicator += 512;
                }
                else {
                    if ( !strl && !strr ) $(this).addClass("merge-bottom");
                    if ( dgse ) {
		    	dgse.addClass("merge-top");
			indicator += 1024;
		    }
                    if ( dgsw ) {
		        dgsw.addClass("merge-top");
			indicator += 2048;
		    }
                }
            }

            console.log(`indicator: ${indicator}`);

        }

        else if ( new_state == false ) {
            if ( !$(this).hasClass("marked") ) return;

            if ( strl ) { 
		strl.removeClass("str-right");
                if ( !stru || !strd ) strl.removeClass("merge-right");
	    }

            if ( dgnw ) {
               if (!strl && !is_touched(linc + 2 * i_left) ) dgnw.removeClass("merge-bottom");
               if (!stru && !is_touched(linc + 2 * i_top)  ) dgnw.removeClass("merge-right");
            }

            if ( stru ) {
                stru.removeClass("str-bottom");
                if ( !strl || !strr ) stru.removeClass("merge-bottom");
            }

            if ( dgne ) {
               if ( !strr && !is_touched(linc + 2 * i_right) ) dgne.removeClass("merge-bottom");
               if ( !stru && !is_touched(linc + 2 * i_top)   ) dgne.removeClass("merge-left");
            }

            if ( strr ) {
                strr.removeClass("str-left");
                if ( !stru || !strd ) strr.removeClass("merge-left");
	    }

            if ( dgse ) {
               if ( !strr && !is_touched(linc + 2 * i_right) ) dgse.removeClass("merge-top");
               if ( !strd && !is_touched(linc + 2 * i_bottom)) dgse.removeClass("merge-left");
            }

            if ( strd ) {
                strd.removeClass("str-top");
                if ( !strl || !strr ) strd.removeClass("merge-top");
	    }

            if ( dgsw ) {
               if ( !strl && !is_touched(linc + 2 * i_left)   ) dgsw.removeClass("merge-top");
               if ( !strd && !is_touched(linc + 2 * i_bottom )) dgsw.removeClass("merge-right");
            }

            $(this).removeClass("merge-left str-left merge-right str-right merge-top str-top merge-bottom str-bottom active-lane");

        }

        $(this).removeClass("marked");

    });
    touched.reset(min_lane_id);
}

$(function () {
    change_state($("table"), null); /* init */
    $("td").on("click", function (e) {
        e.stopImmediatePropagation();
        $(this).toggleClass("marked");
	var recently_marked = $("td.recently-marked").get(0);
        var tbody = $(this).closest("tbody");
	var index = tbody.data("cols") * ($(this).parent().index()-1) + $(this).index() - 1;
        var lane_id = tbody.data("laneids")[ index ] || spare_lane_id+1;
        var touched = tbody.data("touched")[ $(this).hasClass("marked") ? "up" : "down" ](lane_id);
        console.log(`Lane id ${lane_id} now marked ${touched} times.`);
        var x = $(this).closest("tr").children("td").index(this);
        if ( recently_marked != this )
            $(recently_marked).removeClass("recently-marked");
        $(this).toggleClass("recently-marked");
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
    $("fieldset input").on("change", function() {
	$("#sompyler-text").text(
	  "pattern: " + write_lines($("table"))
	  + "\n0: <pattern:" 
	  + ($(".tone-select input:checked").val() || "")
	  + ($(".accidental-select input:checked").val() || "")
	  + ($(".octave-select input:checked").val() || "")
	  + ($(".chord-type-select input:checked").val() || $(".scale-select input:checked").val() || "")
	);
    }).checkboxradio({ icon: false });
    $("fieldset span").controlgroup();
    /* $("#mask").controlgroup(); */
});
