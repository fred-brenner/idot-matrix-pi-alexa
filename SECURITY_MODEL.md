# Battery Guard and iDotMatrix threat model

## Scope and evidence
- User-selected scope: all of `fred-brenner/battery-guard_intact` and `fred-brenner/idot-matrix-pi-alexa`. The user excluded attacks requiring an already-compromised local OS account; other risks remain in scope.
- These are independent local-device applications, not a shared backend. This model uses their READMEs, Android manifest and Kotlin sources, and the Pi bridge, installer, Fauxmo configuration and systemd unit. Architecture below is code/documentation evidence. Explicit user confirmations are separated below.
- Pi deployment evidence is in-repository (`install_pi.sh`, `idotmatrix-alexa.service`, `fauxmo.json`, `idotmatrix-bridge.env.example`). The user confirmed a private home LAN deployment and no separate infrastructure repository. Exact firewall, router, VLAN and SSH configuration is unknown; private LAN is not proof that all LAN peers are trustworthy. Upstream dependencies, Echo/Alexa internals, Android OS and device firmware are external trust boundaries, not separately scanned repositories.

## Components and trust boundaries
1. **Battery BLE** — `battery-guard_intact/app/src/main/java/com/example/batteryguardlite/ble/`: Android BLE scan, device selection, GATT notifications and voltage parsing. Nearby radio advertisements and notification bytes cross into the app; device-name/UUID matching alone is not proof of authenticated physical-device identity.
2. **Battery App and History** — `battery-guard_intact/app/src/main/java/com/example/batteryguardlite/MainActivity.kt`, `history/`, `ui/`, `app/src/main/AndroidManifest.xml` and backup rules: owner-operated UI, permission handling, private daily readings and CSV backup/restore. User-selected document providers/files cross into application parsing; exports leave the app sandbox at the user's chosen destination.
3. **Alexa LAN Service** — `idot-matrix-pi-alexa/fauxmo.json`, `idotmatrixplugin.py`: Fauxmo emulates one WeMo device on TCP port 12340 with local SSDP discovery, accepts on/off requests, persists desired state and schedules one BLE worker. LAN clients cross the network-to-process boundary. Application configuration does not add credentials; deployed reachability and upstream protocol security require confirmation.
4. **Display BLE Bridge** — `idot-matrix-pi-alexa/bridge.py`: CLI limited to on/off/discover, upstream iDotMatrix client, BLE display selection, clock commands and environment-configured address/size. Crosses Pi process-to-BlueZ-to-radio-to-display boundaries. Address pinning is recommended in the README; blank address enables discovery of a nearby IDM device.
5. **Build and Pi Deployment** — Android Gradle files/wrapper, `idot-matrix-pi-alexa/install_pi.sh`, `requirements-pi.txt`, `idotmatrix-alexa.service`, environment template and repository automation if present: dependency acquisition, privileged installation and service launch. Installer invokes sudo; service runs as `pi`, which the README expects to have sudo access. Package registries, GitHub upstream source, system packages and local writable configuration are separate trust sources.

## Entry points and assets
- Battery app: nearby BLE advertisements/GATT data, launcher activity, Android permission decisions, CSV files and document providers selected through the system file picker. No internet permission, cloud endpoint, login or telemetry is documented; the manifest contains Bluetooth and legacy location permissions, not INTERNET.
- Pi bridge: reachable local Fauxmo/SSDP service, permitted local CLI invocations, service/configuration/state files, environment values and installer/dependency update inputs. The user confirmed private home LAN only, so direct internet reachability is out of the stated deployment. Untrusted or compromised LAN peers remain in scope.
- Assets: integrity and availability of live battery readings and the latest 20 daily history points; confidentiality of voltage/date/time history and user-exported CSVs; integrity/availability of display commands and state; Pi host, service account, filesystem and any credentials or other resources that account can reach; software/dependency integrity.
- The user requested no special asset ranking and normal protection for both apps and the Pi host. Retain scanner ratings unless the explicit account-compromise exclusion applies; do not label hardware monitoring safety-critical or assume display nuisance permits host compromise. No user accounts, financial records or cloud credential store are evidenced in these apps, but absence of such data does not make the host unimportant.

## Relevant attacker profiles
- Nearby BLE peer impersonating an expected peripheral or supplying malformed data.
- Untrusted or compromised device with LAN reachability to the Pi; internet attacker only where routing/port exposure or another confirmed path makes it reachable.
- Malicious CSV/document provider, requiring the owner to select a file for restore.
- A contributor or compromised distribution source affecting dependencies/installations remains in scope. Attacks whose prerequisite is an already-compromised local OS account are explicitly excluded by the user. A remote/LAN/BLE/selected-file path that itself compromises an account is not excluded.
- A malicious owner who already has full OS control is a different precondition from a remote attacker. The user excluded only attacks requiring an already-compromised local OS account; scanner exploitability judgments remain authoritative.

## Existing controls and limits evidenced in code/docs
- Android runtime BLE permission checks and OS sandbox; MODE_PRIVATE preferences; automatic app backup disabled in manifest. File access is user-mediated by Android's document picker.
- BLE parser rejects payloads shorter than three bytes and voltage outside 3000–32000 mV. History is capped at 20 dates; CSV import validates expected columns/values and preserves existing dates; Activity limits CSV line count. These are controls, not proof against all malformed input.
- Pi action is restricted to on/off/discover; plugin uses an argument array for subprocess invocation, one worker and one coalesced pending state, not a request-derived shell string. State writes use a temporary file followed by os.replace.
- systemd sets User=pi, Group=pi, NoNewPrivileges=true and PrivateTmp=true, with restart-on-failure. These do not establish sudo policy, least privilege across the host or network isolation.
- Some Python dependencies are pinned; upstream iDotMatrix source follows its current branch via clone/pull. Installer trusts OS repositories and source/package providers. This is a trust boundary, not an asserted vulnerability.

## Out of scope, accepted risk and prioritization
- User-confirmed deployment: private home LAN only; no separate infrastructure repository. No special asset ranking; protect both apps and the Pi host normally.
- User-confirmed exclusion: attacks requiring an already-compromised local OS account. Apply this narrowly: do not dismiss initial compromise, remote/LAN/BLE/CSV attacks or supply-chain attacks merely because they can ultimately gain local execution. No acceptance of nuisance-only display toggling was given.
- User-requested finding tags: Component and CVE when applicable. A CVE value must be a relevant confirmed identifier, not guessed.
- Scan only the two selected repositories; external OS/firmware/services/dependency repositories are context, with integration risks still relevant. This repository boundary is not acceptance of vulnerabilities in in-scope integration code.
- Start each finding at the scanner's severity. Only explicit user facts or user-authored security policy may move it; architectural inferences alone do not. Never raise findings marked hard to exploit or unverified. Consider likelihood/access prerequisites and the affected asset for each reason. Tag findings with the stable Component names above.

## Remaining uncertainty
- Exact LAN trust/isolation, sudo policy, selected BLE address, Android device versions, safety-critical usage and resources/credentials reachable from the Pi are not confirmed.
- These unknowns alone do not move scanner severities.
