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

class Lane {
    /* pitches, lengths */
    constructor() {
	this.pitches = [];
	this.lengths = [];
    }

    add(pitch, length) {
	this.pitches.push(pitch);
	this.lengths.push(length);
    }
}

class LaneFrame {
    /* Lane-Id -> Offsets -> Lanes, Next */
    constructor() {
	this.lanes = {}
    }
    add_lane(numid, offset, pitch, length) {
	if ( numid in this.lanes ) {
	    // this.lanes[numid][offset].add ...
	}
	else {
	    this.lanes[numid] = { offset: [], "Next": null, "MaxLen": 0 }
	}
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
	        if ( strl ) $(this).addClass("str-left merge-left" );
	        if ( stru ) $(this).addClass("str-top merge-top" );
	        if ( strr ) $(this).addClass("str-right merge-right" );
	        if ( strd ) $(this).addClass("str-bottom merge-bottom" );
	        if ( dgne || dgse ) $(this).addClass("merge-right" );
	        if ( dgnw || dgsw ) $(this).addClass("merge-left" );
	        if ( dgnw || dgne ) $(this).addClass("merge-top" );
	        if ( dgsw || dgse ) $(this).addClass("merge-bottom" );
            }
            else {
		if (touched_lanes.includes(lane_ids[linc]))
		    $(this).addClass("active-lane");
		else
                    $(this).removeClass("active-lane");
                return;
            }
        }

        else if ( new_state == false ) {
            if ( !$(this).hasClass("marked") ) return;
            $(this).removeClass("merge-left str-left merge-right str-right merge-top str-top merge-bottom str-bottom active-lane");

        }

	if (dgnw) {
	    dgnw.toggleClass("str-right", !!stru );
	    dgnw.toggleClass("merge-right", new_state || !!stru || !!strl || is_touched(linc + 2 * i_top) );
	    dgnw.toggleClass("str-bottom", !!strl );
	    dgnw.toggleClass("merge-bottom", new_state || !!stru || !!strl || is_touched(linc + 2 * i_left) );
	}
        if (stru) {
	    stru.toggleClass("str-bottom", new_state );
	    stru.toggleClass("merge-bottom", new_state || !!strr || !!strl)
	}
	if (dgne) {
	    dgne.toggleClass("str-left", !!stru );
	    dgne.toggleClass("merge-left", new_state || !!stru || !!strr || is_touched(linc + 2 * i_top) );
	    dgne.toggleClass("str-bottom", !!strr);
	    dgne.toggleClass("merge-bottom", new_state || !!stru || !!strr || is_touched(linc + 2 * i_right) );
	}
        if (strr) {
	    strr.toggleClass("str-left", new_state );
	    strr.toggleClass("merge-left", new_state || !!stru || !!strd);
	}
	if (dgse) {
            dgse.toggleClass("str-left", !!strd);
	    dgse.toggleClass("merge-left", new_state || !!strd || !!strr || is_touched(linc + 2 * i_bottom) );
	    dgse.toggleClass("str-top", !!strr );
	    dgse.toggleClass("merge-top", new_state || !!strd || !!strr || is_touched(linc + 2 * i_right) );
	}
	if (strd) {
	    strd.toggleClass("str-top", new_state );
	    strd.toggleClass("merge-top", new_state || !!strr || !!strl );
	}
	if (dgsw) {
	    dgsw.toggleClass("str-right", !!strd );
	    dgsw.toggleClass("merge-right", new_state || !!strd || !!strl || is_touched(linc + 2 * i_bottom) );
	    dgsw.toggleClass("str-top", !!strl );
	    dgsw.toggleClass("merge-top", new_state || !!strd || !!strl || is_touched(linc + 2 * left) );
	}
	if (strl) {
	    strl.toggleClass("str-right", new_state );
            strl.toggleClass("merge-right", new_state || !!stru || !!strd );
	}

        $(this).removeClass("marked");

    });
    touched.reset(min_lane_id);
    if ( $("input:radio[name=tone]:checked").length > 1 ) write_lines(table.parent());
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
