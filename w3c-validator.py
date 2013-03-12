#!/usr/bin/env python2
'''
w3c-validator - Validate files using the WC3 validators

Copyright: Stuart Rackham (c) 2011
License:   MIT
Email:     srackham@gmail.com
'''

import os
import sys
import time
import json
import commands
import urllib

html_validator_url = 'http://validator.w3.org/check'
css_validator_url = 'http://jigsaw.w3.org/css-validator/validator'
unicorn_validator_url = 'http://validator.w3.org/unicorn/check'

verbose_option = False

def message(msg):
    print >> sys.stderr, msg

def verbose(msg):
    if verbose_option:
        message(msg)

def validate(filename):
    '''
    Validate file and return JSON result as dictionary.
    'filename' can be a file name or an HTTP URL.
    Return '' if the validator does not return valid JSON.
    Raise OSError if curl command returns an error status.
    '''
    quoted_filename = urllib.quote(filename)
    ishtml = filename.endswith('.htm') or filename.endswith('.html')
    ishtml = ishtml or filename.endswith('.xht') or filename.endswith('.xhtml')
    if filename.startswith('http://'):
        # Submit URI with GET.
        if filename.endswith('.css'):
            cmd = ('curl -sG -d uri=%s -d output=json -d warning=0 %s'
                    % (quoted_filename, css_validator_url))
        elif ishtml:
            cmd = ('curl -sG -d uri=%s -d output=json %s'
                    % (quoted_filename, html_validator_url))
        else:
            cmd = ('curl -sG -d ucn_uri=%s -d ucn_task=conformance -d ucn_format=text %s'
                    % (quoted_filename, unicorn_validator_url))
    else:
        # Upload file as multipart/form-data with POST.
        if filename.endswith('.css'):
            cmd = ('curl -sF "file=@%s;type=text/css" -F output=json -F warning=0 %s'
                    % (quoted_filename, css_validator_url))
        elif ishtml:
            cmd = ('curl -sF "uploaded_file=@%s;type=text/html" -F output=json %s'
                    % (quoted_filename, html_validator_url))
        else:
            cmd = ('curl -sF "ucn_file=@%s" -F ucn_task=conformance -F ucn_format=text %s'
                    % (quoted_filename, unicorn_validator_url))
    verbose(cmd)
    status,output = commands.getstatusoutput(cmd)
    if status != 0:
        raise OSError (status, 'failed: %s' % cmd)
    if filename.endswith('.css') or ishtml:
        verbose(output)
    try:
        if filename.endswith('.css'):# or ishtml:
            result = json.loads(output)
        else:
            result = output
    except ValueError:
        result = ''
    time.sleep(2)   # Be nice and don't hog the free validator service.
    return result


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == '--verbose':
        verbose_option = True
        args = sys.argv[2:]
    else:
        args = sys.argv[1:]
    if len(args) == 0:
        message('usage: %s [--verbose] FILE|URL...' % os.path.basename(sys.argv[0]))
        exit(1)
    errors = 0
    warnings = 0
    for f in args:
        message('validating: %s ...' % f)
        retrys = 0
        while retrys < 2:
            result = validate(f)
            if result:
                break
            retrys += 1
            message('retrying: %s ...' % f)
        else:
            message('failed: %s' % f)
            errors += 1
            continue
        if f.endswith('.css'):
            errorcount = result['cssvalidation']['result']['errorcount']
            warningcount = result['cssvalidation']['result']['warningcount']
            errors += errorcount
            warnings += warningcount
            if errorcount > 0:
                message('errors: %d' % errorcount)
            if warningcount > 0:
                message('warnings: %d' % warningcount)
        elif isinstance(result, str):
            print >> sys.stderr, result
            passed = False
            notpassed = False
            for line in result.split('\n'):
                if line.startswith('This document has passed the test:'):
                    passed = True
                elif line.startswith('This document has not passed the test:'):
                    notpassed = True
            errors = 1 if notpassed and not passed else 0
        else:
            for msg in result['messages']:
                if 'lastLine' in msg and 'lastColumn' in msg:
                    message('%(type)s: line %(lastLine)d: column %(lastColumn)d: %(message)s' % msg)
                elif 'lastLine' in msg:
                    message('%(type)s: line %(lastLine)d: %(message)s' % msg)
                else:
                    message('%(type)s: %(message)s' % msg)
                if msg['type'] == 'error':
                    errors += 1
                else:
                    warnings += 1
    if errors:
        exit(1)
