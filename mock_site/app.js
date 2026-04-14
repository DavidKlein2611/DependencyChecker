// Some internal Acme Corp logic
const auth = require('@acmecorp-internal-unregistered-scope-99/auth-handler');
const logger = require('acme-super-secret-logger');

// And some regular public packages
import { useState } from 'react';
const express = require('express');

// Let's add a package with a known registered scope
const known = require('@angular/core');

// Simulate Webpack chunk dictionary
const chunk = {
    7392: function(module, exports, __webpack_require__) {
        "use strict";
        eval("// extracted from node_modules/@acmecorp/hidden-webpack-module/index.js");
    }
};

// Test new Webpack and Vite extractors
__webpack_require__("acme-webpack-require-pkg");
const chunkDict = {
/***/ "acme-webpack-chunk-pkg":
/*!**********************************!*\
  !*** ./src/secret.js ***!
  \**********************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {
        "use strict";
    })
};
const viteMod = __vite_ssr_import__("acme-vite-ssr-pkg");

console.log("App initialized with", auth.name);