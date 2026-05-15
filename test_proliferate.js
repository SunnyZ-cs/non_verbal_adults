const puppeteer = require('puppeteer');

(async () => {
    // Launch browser
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
    
    // Serve files locally? No, let's just open the raw HTML using file://
    const path = require('path');
    const fileUrl = 'file://' + path.resolve('pilot1/index.html');
    
    await page.goto(fileUrl, { waitUntil: 'networkidle0' });
    
    // Simulate finishing the experiment
    await page.evaluate(() => {
        try {
            const final_data = { test: 123 };
            console.log("Calling proliferate.submit...");
            proliferate.submit(final_data);
            console.log("proliferate.submit success!");
        } catch (e) {
            console.error("CAUGHT ERROR:", e.message);
        }
    });

    await browser.close();
})();
