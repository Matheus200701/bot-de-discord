# Discord Compatibility — 2026-09-06

## Audit status

The implementation is based on the current official Discord Developer Platform documentation and the September 2026 developer changelog.

| Area | Status | Decision |
|---|---|---|
| Slash/User/Message commands | SUPPORTED | Use Application Commands |
| Entry Point commands | SUPPORTED | Reserve for Activities only |
| Buttons/selects/modals | SUPPORTED | Use current component model |
| Components V2 | SUPPORTED | Optional; keep legacy components where simpler |
| User install | SUPPORTED | Enable only for commands that work without guild state |
| Guild install | SUPPORTED | Primary commerce deployment mode |
| OAuth2 | SUPPORTED | Authorization-code flow for dashboard/account linking |
| Account Linking on Web | SUPPORTED | Optional external-account integration |
| Premium Apps | REQUIRES_ELIGIBILITY | Not the default checkout rail |
| Premium App one-time purchases | REQUIRES_ELIGIBILITY | Separate from external commerce orders |
| Premium App subscriptions | REQUIRES_ELIGIBILITY | Separate domain/provider adapter |
| Activities | OPTIONAL | Only if showroom/configurator provides real value |
| Social SDK | NOT_REQUIRED | Not a Python Discord bot dependency |
| Add/Remove Guild Member Role | SUPPORTED | Requires `MANAGE_ROLES`; hierarchy and managed-role rules still apply |
| Guild Member listing | PRIVILEGED_INTENT | Avoid for fulfillment; direct role mutation is sufficient |
| Private channel obfuscation | UPCOMING_BREAKING | Do not assume hidden channels are fully readable; target Nov 2026 behavior |
| Privileged intents | MINIMIZE | Request only when needed; review threshold is user-based |

## Important current changes

- Discord documents both `GUILD_INSTALL` and `USER_INSTALL` contexts. User-installed apps can appear in servers, DMs and group DMs while respecting the invoking user's permissions.
- Discord currently documents a broad Components V2 system including containers, sections, text display, media galleries, file upload, radio groups and checkbox components. Components V2 messages use the `IS_COMPONENTS_V2` flag and have different content/embed semantics.
- Discord announced channel obfuscation for bots in August 2026; HTTP channel listing will omit channels the bot cannot view starting November 16, 2026. The application must not rely on visibility into inaccessible channels.
- Privileged intent review changed in June 2026: the threshold is based on accessible users rather than guild count, with annual reapplication after review.
- Discord's developer changelog records a September 3, 2026 increase of the default file upload limit from 10 MiB to 20 MiB.

## Fase 8 fulfillment

Role delivery uses the official guild-member role mutation endpoints. The application does not request `ADMINISTRATOR`; it requires `MANAGE_ROLES`, avoids managed roles, and relies on Discord's role hierarchy enforcement. Fulfillment is asynchronous and idempotent through the platform's PostgreSQL outbox. No privileged member-listing intent is needed for direct fulfillment.

## API version

Use the current Discord API documented by Discord. Do not hard-code undocumented endpoints. Library compatibility is validated through the pinned Python dependency range and CI.

## Payment distinction

Discord Premium Apps monetization is not a general-purpose merchant checkout for arbitrary store inventory. The commerce engine therefore keeps external PSPs (PIX/Mercado Pago/Stripe/etc.) behind `PaymentProvider`, while Discord Premium App SKUs are an optional, separate integration subject to Discord eligibility and policies.
