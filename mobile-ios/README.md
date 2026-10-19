# MYRA Mobile — iOS SwiftUI source scaffold

The first source scaffold lives in `MyraMobile/`. It is not an Xcode project yet and has not been compiled on Windows.

## Create the Xcode project

1. On a Mac, open Xcode and create **iOS App** named `MyraMobile`, interface **SwiftUI**, language **Swift**, deployment target **iOS 17** or later.
2. Add `MyraMobileApp.swift`, `ContentView.swift` and `RemoteAPI.swift` to the app target.
3. Build and run in the iOS Simulator before configuring remote access.
4. Configure the Windows backend with `MYRA_REMOTE_API_TOKEN` as described in `../PHASE28_3_IOS.md`.
5. Use the HTTPS MagicDNS URL for the Tailscale Serve path `/remote/v1`, and paste the token into the app. The app stores the token in iOS Keychain.

## Current scope

- Connection settings and API token input.
- Status refresh every five seconds.
- Start and cancel task.
- Keychain token storage.
- HTTPS enforced for remote endpoints; plain HTTP is accepted only for loopback development.
- No screenshot upload, notification, Siri, Lock Screen widget, or Home Screen widget yet.

Do not expose the FastAPI root to the tailnet. Use a path-scoped Tailscale Serve endpoint for `/remote/v1` only, and never use Funnel for this private control API.
