#!/usr/bin/env python3

import argparse
import csv
import io
import os
import platform
import socket
import subprocess
import sys

def main(args):
    os_family           = platform.linux_distribution()[0]

    if args.daemon == 'chronyc':
        if args.resource == 'leap_status':
            chronyc_monitoring     = chronycTracking()

            resultToIcinga(chronyc_monitoring)

        elif args.resource == 'sources':
            sources_monitoring = chronycSources('sources')

            resultToIcinga(sources_monitoring)

        elif args.resource == 'falseticker':
            sources_monitoring = chronycSources('falseticker')

            resultToIcinga(sources_monitoring)

    elif args.daemon == 'systemd-timesyncd':
        if args.resource == 'leap_status':
            timesyncd_monitoring = timedatectlStatus()

            resultToIcinga(timesyncd_monitoring)

        else:
            print('Unsupported systemd-timesyncd resource. Supported resources: leap_status')
            sys.exit(3)


def chronycMonitor(chronyc_command):
    chronyc_stdout  = subprocess.Popen([ 'chronyc', '-c', chronyc_command ], stdout=subprocess.PIPE)
    chronyc_o       = io.TextIOWrapper(chronyc_stdout.stdout, newline=os.linesep)
    chronyc_o_csv   = csv.reader((line for line in chronyc_o), delimiter=',')

    return list(chronyc_o_csv)


def chronycSources(chk_resource):
    # TODO: Support thresholds from the cmd line

    chronyc_status              = chronycMonitor('sources')
    chronyc_sources             = len(chronyc_status)
    sources_out                 = {}
    sources_out['service']      = {}
    sources_out['perfd']        = {}

    if chk_resource == 'falseticker':
        falseticker_msg             = 'All of the configured sources are falseticker'
        falseticker_status          = 2
        falseticker_cnt             = 0
    elif chk_resource == 'sources':
        c_sources_msg               = 'No synced source.'
        c_sources_status            = 2
        c_sources_available         = 0
        c_sources_unavailable       = 0
        c_sources_synchronized      = 0
        c_sources_unreliable        = 0

    sources_configured = 0

    for s in chronyc_status:
        s_status    = s[1]
        s_host      = s[2]

        sources_configured += 1

        if chk_resource == 'falseticker':
            if s_status in ('x'):
                falseticker_cnt += 1
        elif chk_resource == 'sources':
            if s_status in ('+', '-', '*'):
                c_sources_available += 1
                if s_status == '*':
                    c_sources_synchronized += 1
            elif s_status in ('?'):
                c_sources_unavailable += 1
            elif s_status in ('~'):
                c_sources_unreliable += 1

    if chk_resource == 'falseticker':

        if falseticker_cnt == 0:
            falseticker_status  = 0
            falseticker_msg     = 'No falseticker found'
        elif falseticker_cnt < sources_configured:
            falseticker_status  = 1
            falseticker_msg     = '{} falseticker found'.format(falseticker_cnt)

        r_name      = 'NTP Falseticker Status'
        r_status    = falseticker_status
        r_msg       = falseticker_msg

    elif chk_resource == 'sources':

        r_name = 'NTP Sources Status'

        if c_sources_unavailable <= sources_configured // 2:

            if c_sources_synchronized > 0:
                c_sources_status  = 0
                c_sources_msg     = '{} out of {} sources are available; {} synchronized source'.format(c_sources_available, sources_configured, c_sources_synchronized)
        elif c_sources_unavailable <= sources_configured - 1:

            if c_sources_synchronized > 0:
                c_sources_status  = 1
                c_sources_msg     = '{} out of {} sources are available; {} synchronized source'.format(c_sources_available, sources_configured, c_sources_synchronized)

        r_name      = 'NTP Sources Status'
        r_status    = c_sources_status
        r_msg       = c_sources_msg

    sources_out['service']['name']                              = r_name
    sources_out['service']['state']                             = r_status
    sources_out['service']['msg']                               = r_msg

    if chk_resource == 'falseticker':
        sources_out['perfd']['falseticker_sources']             = {}
        sources_out['perfd']['falseticker_sources']['value']    = falseticker_cnt
        sources_out['perfd']['falseticker_sources']['max']      = sources_configured
        sources_out['perfd']['falseticker_sources']['crit']     = sources_configured
        sources_out['perfd']['configured_sources']              = {}
        sources_out['perfd']['configured_sources']['value']     = sources_configured
        sources_out['perfd']['configured_sources']['max']       = sources_configured
    elif chk_resource == 'sources':
        sources_out['perfd']['available_sources']               = {}
        sources_out['perfd']['available_sources']['value']      = c_sources_available
        sources_out['perfd']['available_sources']['max']        = sources_configured
        sources_out['perfd']['available_sources']['warn']       = sources_configured // 2
        sources_out['perfd']['available_sources']['crit']       = 0
        sources_out['perfd']['synchronized_sources']            = {}
        sources_out['perfd']['synchronized_sources']['value']   = c_sources_synchronized
        sources_out['perfd']['synchronized_sources']['max']     = sources_configured
        sources_out['perfd']['unavailable_sources']             = {}
        sources_out['perfd']['unavailable_sources']['value']    = c_sources_unavailable
        sources_out['perfd']['unavailable_sources']['max']      = sources_configured
        sources_out['perfd']['unavailable_sources']['warn']     = sources_configured // 2
        sources_out['perfd']['unavailable_sources']['crit']     = sources_configured - 1
        sources_out['perfd']['unreliable_sources']              = {}
        sources_out['perfd']['unreliable_sources']['value']     = c_sources_unreliable
        sources_out['perfd']['unreliable_sources']['max']       = sources_configured
        sources_out['perfd']['configured_sources']              = {}
        sources_out['perfd']['configured_sources']['value']     = sources_configured
        sources_out['perfd']['configured_sources']['max']       = sources_configured

    return sources_out


def chronycTracking():
    chronyc_status          = chronycMonitor('tracking')
    leap_status             = 0 if chronyc_status[0][13] == 'Normal' else 1
    system_time             = chronyc_status[0][4]
    root_delay              = chronyc_status[0][10]
    root_dispersion         = chronyc_status[0][11]
    max_estimated_error     = float(system_time) + float(root_dispersion) / 2 + float(root_dispersion)
    tracking_out            = {}
    tracking_out['service'] = {}
    tracking_out['perfd']   = {}
    tracking_msg            = 'System clock is not in sync'
    tracking_status         = 2

    if leap_status == 0:
        tracking_status = 0
        tracking_msg    = 'System clock is in sync.'

    tracking_out['service']['name']                         = 'Leap Status'
    tracking_out['service']['state']                        = tracking_status
    tracking_out['service']['msg']                          = tracking_msg

    tracking_out['perfd']['leap_status']                    = {}
    tracking_out['perfd']['leap_status']['value']           = leap_status
    tracking_out['perfd']['leap_status']['max']             = 2
    tracking_out['perfd']['leap_status']['crit']            = 2

    tracking_out['perfd']['max_estimated_error']            = {}
    tracking_out['perfd']['max_estimated_error']['value']   = max_estimated_error

    return tracking_out


def timedatectlStatus():
    tdctl_stdout            = subprocess.Popen(['timedatectl', 'status'], stdout=subprocess.PIPE)
    tdctl_out               = {}
    tdctl_out['service']    = {}
    tdctl_out['perfd']      = {}
    tdctl_msg               = 'System clock is not in sync.'
    tdctl_status            = 2

    for line in io.TextIOWrapper(tdctl_stdout.stdout, encoding='UTF-8'):
        if line.lstrip().startswith('NTP synchronized'):
             if line.split(': ')[1] == 'yes\n':
                 tdctl_status   = 0
        elif line.lstrip().startswith('System clock synchronized'):
             if line.split(': ')[1] == 'yes\n':
                 tdctl_status   = 0

    if tdctl_status == 0:
        tdctl_msg = 'System clock is in sync'

    tdctl_out['service']['name']                = 'Leap Status'
    tdctl_out['service']['state']               = tdctl_status
    tdctl_out['service']['msg']                 = tdctl_msg

    tdctl_out['perfd']['leap_status']           = {}
    tdctl_out['perfd']['leap_status']['value']  = tdctl_status
    tdctl_out['perfd']['leap_status']['max']    = 2
    tdctl_out['perfd']['leap_status']['crit']   = 2

    return tdctl_out


def resultToIcinga(svc_result):
    svc_dict    = svc_result['service']
    chk_name    = svc_dict['name']
    chk_state   = svc_dict['state']
    chk_msg     = svc_dict['msg']

    if chk_state == 0:
        chk_state_str  = 'OK'
    elif chk_state == 1:
        chk_state_str  = 'WARNING'
    elif chk_state == 2:
        chk_state_str  = 'CRITICAL'
    elif chk_state == 3:
        chk_state_str  = 'UNKNOWN'
    else:
        chk_state      = 2
        chk_state_str  = 'Invalid check result'

    if 'perfd' in svc_result:

        pdata_str = None

        for k, v in svc_result['perfd'].items():

            if 'value' not in v:
                # invalid perfdata, missing value; do not process it
                continue

            label       = k

            pd_substr   = '{0}={1}'.format(label, v['value'])

            # set sane defaults for min, max, warn & crit as fallback
            if 'min' not in v:
                pd_substr   = ';'.join([pd_substr, '0'])
            else:
                pd_substr   = ';'.join([pd_substr, str(v['min'])])

            if 'max' not in v:
                pd_substr   = ';'.join([pd_substr, ''])
            else:
                pd_substr   = ';'.join([pd_substr, str(v['max'])])

            if 'warn' not in v:
                pd_substr   = ';'.join([pd_substr, ''])
            else:
                pd_substr   = ';'.join([pd_substr, str(v['warn'])])

            if 'crit' not in v:
                pd_substr   = ';'.join([pd_substr, ''])
            else:
                pd_substr   = ';'.join([pd_substr, str(v['crit'])])

            if not pdata_str:
                pdata_str = pd_substr
            else:
                pdata_str = ' '.join([pdata_str, pd_substr])

    chk_output = '{0} {1} - {2} | {3}'.format(chk_name.upper(), chk_state_str, chk_msg, pdata_str)

    print(chk_output)

    if chk_state == 0:
        sys.exit(0)
    elif chk_state == 1:
        sys.exit(1)
    elif chk_state == 2:
        sys.exit(2)
    else:
        sys.exit(3)

def parseArgs():
    argParser = argparse.ArgumentParser(description='Check the chronyc or systemd-timesyncd sync status.')
    argParser.add_argument('-d', '--daemon', dest='daemon', required=True, type=str, \
                            choices=[ 'chronyc', 'systemd-timesyncd' ], \
                            help='Monitored daemon.')
    argParser.add_argument('-r', '--resource', dest='resource', type=str, default='leap_status', \
                            choices=[ 'leap_status', 'sources', 'falseticker' ], \
                            help='Checked resource. \
                                  Supported options for chronyc: leap_status, sources, falseticker. \
                                  Supported options for systemd-timesyncd: leap_status')

    return argParser.parse_args()


if __name__ == "__main__":
    args = parseArgs()
    main(args)
