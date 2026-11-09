# Repository Now blocker rendering

Refs [Relay #101](https://github.com/egohygiene/relay/issues/101) and
[#27](https://github.com/egohygiene/relay/issues/27).

The supported Observatory `views.now.blockers` array contains enriched directed
relationships: `id`, `type`, public `source` and `target` entity references,
relationship assertion/freshness and provenance. These are not plain entities.
The existing generic record card previously read `title`, `kind` and `state`
directly from the relationship, displaying “Untitled record” and unknown entity
fields even when complete blocker evidence was supplied.

The shared site record renderer now recognizes supplied `blocks` and `depends-on`
relationships. It renders the declared source → target direction and both
canonical endpoint labels, identities, repositories, independent states,
assertions, freshness and permitted source links. Relationship assertion and
freshness remain separate. The stable `data-entity-id` stays the relationship's
own ID, preserving `?entity=relationship:…` selection; filters retain endpoint
states/kinds and relationship facets. Native provenance IDs remain inspectable.
No graph state, edge, relationship direction or endpoint truth is modified.

Both endpoint visibility declarations are inspected before identity or prose.
Private, internal or unclassified endpoints are omitted without names or
placeholders. An incomplete public relationship receives a bounded unavailable
card rather than an invented endpoint state. Existing entity cards retain their existing path.
The implementation reuses shared escaping, URL handling and visual classes;
it adds no provider access, source collection, route, asset or deployment work.

The user deferred tests, runtime/build execution and polish. This bounded change
received Python syntax parsing, whitespace and static source inspection only.
The later qualification pass still needs real populated Now evidence, hostile
and malformed inputs, private endpoint invariance, selection/filter behavior,
keyboard/mobile rendering and static/no-JavaScript review. No browser or native
runtime result is claimed.
