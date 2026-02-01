#!/usr/bin/env node

/**
 * XSS Prevention Test Suite
 *
 * Tests that HTML escaping prevents XSS attacks in NPC responses.
 */

// Simulate the app.js functions
function escapeHTML(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function parseVoiceAnnotations(text) {
    // SECURITY: Escape HTML first to prevent XSS attacks
    const escapedText = escapeHTML(text);

    // Match annotations in square brackets
    const annotationRegex = /\[([^\]]+)\]/g;

    return escapedText.replace(annotationRegex, (match, content) => {
        const lowerContent = content.toLowerCase();
        let elevenLabsEffect = 'none';

        if (lowerContent.includes('static')) {
            elevenLabsEffect = 'radio_static';
        } else if (lowerContent.includes('breathing')) {
            elevenLabsEffect = 'breathing';
        } else if (lowerContent.includes('alarm')) {
            elevenLabsEffect = 'sfx_alarm';
        }

        return `<span class="voice-annotation" data-elevenlabs-effect="${elevenLabsEffect}">${match}</span>`;
    });
}

// Test cases
const testCases = [
    {
        name: "Script tag injection",
        input: "<script>alert('XSS')</script>Hello",
        shouldNotContain: ["<script>"],
        shouldContain: ["&lt;script&gt;"],
        description: "Script tags should be escaped"
    },
    {
        name: "Image tag with onerror",
        input: '<img src=x onerror="alert(1)">',
        shouldNotContain: ["<img"],
        shouldContain: ["&lt;img"],
        description: "Image tags with event handlers should be escaped"
    },
    {
        name: "Event handler injection",
        input: '<div onload="alert(1)">Text</div>',
        shouldNotContain: ["<div"],
        shouldContain: ["&lt;div"],
        description: "Event handlers should be escaped"
    },
    {
        name: "JavaScript URL",
        input: '<a href="javascript:alert(1)">Click</a>',
        shouldNotContain: ["<a"],
        shouldContain: ["&lt;a", "javascript:alert"],
        description: "JavaScript URLs should be escaped"
    },
    {
        name: "Data URL with script",
        input: '<iframe src="data:text/html,<script>alert(1)</script>">',
        shouldNotContain: ["<iframe", "<script>"],
        shouldContain: ["&lt;iframe"],
        description: "Data URLs should be escaped"
    },
    {
        name: "Safe text with annotation",
        input: "The oxygen is low [static] We need to act fast!",
        shouldContain: ['<span class="voice-annotation"', "[static]"],
        description: "Safe annotations should work correctly"
    },
    {
        name: "Mixed: annotation + malicious code",
        input: "Warning! [alarm] <script>alert('pwned')</script>",
        shouldContain: ['<span class="voice-annotation"'],
        shouldNotContain: ["<script>alert"],
        shouldContain: ["&lt;script&gt;"],
        description: "Annotations should work while scripts are escaped"
    },
    {
        name: "HTML entity injection",
        input: "Text &#60;script&#62;alert(1)&#60;/script&#62;",
        shouldNotContain: ["<script"],
        description: "Already-encoded entities should remain escaped"
    },
    {
        name: "Angle brackets in text",
        input: "If x < 5 and y > 10, then...",
        shouldContain: ["&lt;", "&gt;"],
        shouldNotContain: ["x < 5", "y > 10"],  // Should be escaped
        description: "Angle brackets in normal text should be escaped"
    },
    {
        name: "Nested tags",
        input: '<div><script src="evil.js"></script></div>',
        shouldNotContain: ["<div>", "<script"],
        shouldContain: ["&lt;div&gt;", "&lt;script"],
        description: "Nested tags should all be escaped"
    }
];

// Run tests
console.log('\n' + '='.repeat(70));
console.log('🛡️  XSS PREVENTION TEST SUITE');
console.log('='.repeat(70) + '\n');

let passCount = 0;
let failCount = 0;
const failures = [];

testCases.forEach((test, index) => {
    const output = parseVoiceAnnotations(test.input);
    let passed = true;
    const testFailures = [];

    // Check shouldContain
    if (test.shouldContain) {
        test.shouldContain.forEach(str => {
            if (!output.includes(str)) {
                passed = false;
                testFailures.push(`Missing: "${str}"`);
            }
        });
    }

    // Check shouldNotContain
    if (test.shouldNotContain) {
        test.shouldNotContain.forEach(str => {
            if (output.includes(str)) {
                passed = false;
                testFailures.push(`Should not contain: "${str}"`);
            }
        });
    }

    const status = passed ? '✅ PASS' : '❌ FAIL';
    console.log(`${status} Test ${index + 1}: ${test.name}`);
    console.log(`  ${test.description}`);

    if (!passed) {
        console.log(`  Input:  ${test.input}`);
        console.log(`  Output: ${output}`);
        testFailures.forEach(failure => {
            console.log(`  ⚠️  ${failure}`);
        });
        failures.push({ name: test.name, failures: testFailures });
    }

    console.log('');

    if (passed) {
        passCount++;
    } else {
        failCount++;
    }
});

// Summary
console.log('='.repeat(70));
console.log('TEST SUMMARY');
console.log('='.repeat(70));
console.log(`Total: ${testCases.length} tests`);
console.log(`✅ Passed: ${passCount}`);
console.log(`❌ Failed: ${failCount}`);

if (failCount === 0) {
    console.log('\n🎉 ALL TESTS PASSED - XSS attacks successfully blocked!');
    process.exit(0);
} else {
    console.log('\n⚠️  SOME TESTS FAILED:');
    failures.forEach(failure => {
        console.log(`\n  ${failure.name}:`);
        failure.failures.forEach(f => console.log(`    - ${f}`));
    });
    process.exit(1);
}
