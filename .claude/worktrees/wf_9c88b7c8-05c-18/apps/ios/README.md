# iOS app

The Xcode project itself ships under [tasks/08-ios/01-ios-skeleton.md](../../tasks/08-ios/01-ios-skeleton.md). The files committed here today are CD plumbing only — fastlane lanes and a `Gemfile` — so the deploy workflow has something to invoke once 08.01 lands.

## What's in place

- `fastlane/Fastfile` — `beta` lane uploads to TestFlight via match + App Store Connect API. The `release` lane intentionally errors; we'll wire it when we're ready to submit for App Store review.
- `fastlane/Appfile` — reads `APP_IDENTIFIER`, `APPLE_ID`, `TEAM_ID`, `ITC_TEAM_ID` from env so nothing about the team is committed.
- `Gemfile` — pinned fastlane 2.225 + cocoapods 1.15.
- `.github/workflows/ios-release.yml` — `workflow_dispatch`-only, runs `bundle exec fastlane <lane>` on a `macos-14` runner with Xcode 16.

## Required GitHub secrets (set when wiring up)

| Secret | What it is |
| ------ | ---------- |
| `APP_STORE_CONNECT_API_KEY_ID` | Key id from App Store Connect → Users and Access → Keys |
| `APP_STORE_CONNECT_ISSUER_ID` | Issuer id from the same page |
| `APP_STORE_CONNECT_API_KEY` | Base64-encoded contents of the `.p8` file |
| `MATCH_PASSWORD` | Decryption password set when you ran `fastlane match init` |
| `MATCH_GIT_BASIC_AUTH` | Base64-encoded `user:token` for the private match repo |
| `KEYCHAIN_PASSWORD` | Random string used to create the CI keychain |

## One-time match setup (manual)

```
cd apps/ios
bundle install
bundle exec fastlane match init   # picks the match repo
bundle exec fastlane match appstore   # provisions the cert + profile
```

The match repo is private and separate from this repo. Don't reuse the main repo for code-signing material.
