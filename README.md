# check_linux_timesync
Nagios and Icinga2 plugin to check status of the local timesync client. Currently supported timesync clients are systemd-timesyncd and chronyc.

## Dependencies
This plugin requires:
  - one of the following running timesync-clients:
    - chronyc
    - systemd-timesyncd
  - Python3

## Notes
  - `timedatectl` provides less details and insights regarding the configured sources, their state and the dispersion and delay for example. Therefore there are less metrics available for `systemd-timesyncd`.
  - `chronyc` offers a lot of metrics and details regarding the configured sources. See [docs.fedoraproject.org](https://docs.fedoraproject.org/en-US/Fedora/18/html/System_Administrators_Guide/sect-Checking_if_chrony_is_synchronized.html) for a chrony monitoring guide.
  - `leap_status` is used as alias for the sync status of any timesync client (not only chrony, where you find `Leap status` in the output of `chronyc tracking`.
  - The thresholds are currently **not** configurable! So any of the following condition can raise an alarm:
    - conditions for the plugin to succeed (-> exit status OK)
      - chronyc
        - if the client is synced
        - if there are no *falsetickers*
        - if less than half of the configured sources are available
    - conditions for warning alarms
      - chronyc
        - if any false ticking sources are found and the number of those *falsetickers* is less than the number of configured sources
        - if the number of unavailable sources is greater than `configured sources / 2` and less than `configured sources`
      - systemd-timesyncd
        - *None*
    - conditions for critical alarms
      - chronyc
        - if the client is not synced (`leap_status` = 2)
        - if all configured sources are tagged as *falseticker* (see `chronyc sources`)
        - if 50% or less of the configured sources are unavailable
      - sytemd-timesyncd
        - if the client is not synced (`leap_status` = 2)

## How it works

### chronyc checks
The plugin uses `chronyc -c` with the chosen resource (`falseticker`, `leap_status`, `sources`) as argument and parses the output.

### systemd-timesyncd checks
The plugin uses `timedatectl status` command and checks the value of `NTP synchronized` or `System clock synchronized` which is used on older versions.

## Performance data
This plugin provides different metrics depending on the timesync client and checked resource.

### chronyc performance data
Performance data per resource:

  - leap_status
    - leap_status (which matches the plugin exit status: 0 = synced; 2 = not synced)
    - max_estimated_error
  - falseticker
    - configured_sources
    - falseticker_sources
  - sources
    - available_sources
    - configured_sources
    - synchronized_sources
    - unavailable_sources
    - unreliable_sources

### systemd-timesyncd
Only the leap status of the systemd-timesyncd client is monitored. Available metrics:
  - leap_status

## Usage
See the examples below or execute the plugin with -h/--help.

## Examples
Check systemd-timesyncd leap_status:
```
./check_linux_timesync_status  -d systemd-timesyncd
LEAP STATUS OK - System clock is in sync | leap_status=0;0;2;;2
```

Check chronyc falseticker:
```
./check_linux_timesync_status  -d chronyc -r falseticker
NTP FALSETICKER STATUS OK - No falseticker found | falseticker_sources=0;0;4;;4 configured_sources=4;0;4;;
```

Check chronyc leap_status:
```
./check_linux_timesync_status  -d chronyc
LEAP STATUS OK - System clock is in sync. | leap_status=0;0;2;;2 max_estimated_error=0.019269515;0;;;
```

Check chronyc sources with 4 configured sources:
```
./check_linux_timesync_status  -d chronyc -r sources
NTP SOURCES STATUS OK - 4 out of 4 sources are available; 1 synchronized source | available_sources=4;0;4;2;0 synchronized_sources=1;0;4;; unavailable_sources=0;0;4;2;3 unreliable_sources=0;0;4;; configured_sources=4;0;4;;
```
