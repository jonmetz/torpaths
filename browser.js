var page = require('webpage').create(),
    system = require('system'),
    address = null;

if (system.args.length === 1) {
    console.log('Usage: browser.js <some URL>');
    phantom.exit(1);
} else {
    address = system.args[1];
    page.onResourceRequested = function (req) {

	console.log(JSON.stringify(req["url"], undefined, 4));
    };

    page.open(address, function (status) {
	window.setTimeout(function () {
            //page.render();
            phantom.exit();
	    if (status !== 'success') {
		console.log('FAIL to load the address');
		console.log(status);
	    }
	    phantom.exit();
        }, 4000);

    });
}
