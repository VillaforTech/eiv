# Security model

EIV is a local research simulator. It never performs the requested file or
message operation. Its decisions are not authentication, capability tokens,
or production authorization. A session digest is an unkeyed replay checksum.

The trust boundary is explicit: supplied candidate meanings and facts are
unverified inputs. Correct checking cannot repair omitted intent. Unsupported
syntax, unknown conditions, contradictory permissions and exhausted checking
bounds produce abstention. Deliberately omitted candidates can still produce
wrong consensus; this is a documented research result.

The HTTP workbench binds to loopback. It validates Host/Origin, caps bodies,
rejects duplicate JSON keys and ambiguous framing, and bounds connections and
read time. Do not expose this standard-library development server publicly.
The portfolio page is a static educational presentation and can be hosted
independently of the workbench.

Use a minimal synthetic reproduction when reporting a vulnerability. Never
include real credentials, private instructions or personal data. Contact the
maintainer through [their profile](https://github.com/VillaforTech) for a private
disclosure route before posting sensitive details publicly.

Version 0.4 is the maintained research line. Archived experiment sources are
retained only for isolated reproduction and do not inherit current hardening.
