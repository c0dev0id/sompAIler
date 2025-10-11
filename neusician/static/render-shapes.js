$(function() {
	var shapeform = document.forms[0];
	$(shapeform).submit(function (e) {
            e.preventDefault();
	    $("#result").text("Loading ...");
	    console.log("ready to fetch");
	    fetch("render-shapes", {
                method: "POST",
		/* headers: {
		    "Content-Type": "application/x-www-form-urlencoded",
		}, */
		body: new FormData(shapeform),
	    }).then(function (response) {
		if (response.ok) 
		    return response.text();
		else {
		    return $(response.text()).find("pre").get(0);
		}
	    }).then(function (svgText) {
		document.querySelector("#result").innerHTML = svgText;
	    }).catch(err => {
		document.querySelector("#result").innerText = err;
	    });
	});
});
