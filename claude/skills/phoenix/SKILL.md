---
name: phoenix
description: |
  Full-stack Elixir/Phoenix development skill for LiveView applications.
  Covers: Elixir idioms, Mix workflow, Phoenix conventions, Ecto patterns,
  LiveView, HEEx templates, forms, testing, JS/CSS integration, and UI/UX.
  Use when: writing LiveViews, Ecto schemas, migrations, Phoenix routes,
  HEEx templates, or reviewing Elixir code quality.
version: 1.0.0
date: 2026-03-01
user-invocable: true
---

# Phoenix Development

Full-stack guidance for production Phoenix + LiveView applications. Covers the Elixir language layer, Phoenix framework conventions, Ecto data access, LiveView interactivity, HEEx templating, forms, and testing.

For API contract design and HTTP semantics, see `/api-design`. For domain modeling and schema evolution, see `/domain-design`. For responsive CSS and Tailwind v4, see `/css-responsive`. For design system and accessibility, see `/ux-design`. For observability, see `/observability`.

---

## 1. Elixir Idioms

- Variables are immutable but rebindable — block expressions (`if`, `case`, `cond`) must bind their result to use it:

  ```elixir
  # WRONG — rebinding inside `if` has no effect outside
  if connected?(socket), do: socket = assign(socket, :val, val)

  # RIGHT — bind the block result
  socket = if connected?(socket), do: assign(socket, :val, val), else: socket
  ```

- Lists do not support index-based access (`list[i]`). Use `Enum.at/2`, pattern matching, or `hd/tl`
- One module per file — convention for readability and clean compilation order
- Never use map access syntax (`struct[:field]`) on structs — use `struct.field` or higher-level APIs like `Ecto.Changeset.get_field/2`
- Predicate functions: end with `?`, no `is_` prefix (reserve `is_` for guards)
- Never use `String.to_atom/1` on user input — unbounded atom creation leaks memory
- OTP primitives (`DynamicSupervisor`, `Registry`) require names in child specs
- `Task.async_stream/3` for concurrent enumeration with back-pressure — usually pass `timeout: :infinity`
- Elixir's `Date`, `Time`, `DateTime`, `Calendar` cover most needs — no extra deps unless parsing is required (`date_time_parser`)
- Elixir has `if/else` but **no `else if` or `elsif`** — use `cond` or `case` for multiple branches

## 2. Mix & Dependencies

- Run `mix help <task>` before using unfamiliar tasks
- Debug test failures: `mix test test/path.exs` or `mix test --failed`
- `mix deps.clean --all` is almost never needed — avoid unless justified
- `mix precommit` for pre-commit checks (project alias)
- Use `Req` for HTTP requests — never `HTTPoison`, `Tesla`, or `:httpc`

## 3. Phoenix Conventions

- Router `scope` blocks include an optional alias prefix — no manual `alias` needed for route modules:

  ```elixir
  scope "/admin", AppWeb.Admin do
    pipe_through :browser
    live "/users", UserLive, :index  # resolves to AppWeb.Admin.UserLive
  end
  ```

- `Phoenix.View` is removed — do not use it
- `Layouts` module is aliased in `*_web.ex` — wrap LiveView templates with `<Layouts.app flash={@flash} ...>`
- Always use the imported `<.icon name="hero-x-mark" />` component — never `Heroicons` modules
- Always use the imported `<.input>` component from `core_components.ex`
- If you override `<.input>` classes, no defaults are inherited — your classes must fully style it
- `<.flash_group>` lives in `layouts.ex` only — never call it elsewhere
- Fix `current_scope` errors by moving routes to the proper `live_session` and passing `current_scope` to `<Layouts.app>`

## 4. Ecto Patterns

- Always preload associations in queries when accessed in templates
- `import Ecto.Query` in seeds, scripts, and anywhere you write queries
- Schema fields use `:string` type even for `:text` columns
- `validate_number/2` does not support `:allow_nil` — validations only run when the field has a non-nil change
- Access changeset fields with `Ecto.Changeset.get_field/2` — never `changeset[:field]`
- Fields set programmatically (e.g., `user_id`) must not appear in `cast` — set them explicitly when creating the struct

## 5. LiveView

- Name LiveViews with `Live` suffix: `AppWeb.WeatherLive`
- The default `:browser` scope is aliased with `AppWeb` — just `live "/weather", WeatherLive`
- Never use deprecated `live_redirect`/`live_patch` — use `<.link navigate={}>`, `<.link patch={}>`, `push_navigate`, `push_patch`
- Avoid LiveComponents unless there is a strong, specific need
- When using `phx-hook="MyHook"`, always set `phx-update="ignore"` on the same element
- Never write `<script>` tags in HEEx — put JS in `assets/js/` and integrate via `app.js`

### Streams

Streams are mandatory for collections — never assign raw lists:

- Append: `stream(socket, :items, [new_item])`
- Prepend: `stream(socket, :items, [new_item], at: 0)`
- Reset: `stream(socket, :items, new_items, reset: true)`
- Delete: `stream_delete(socket, :items, item)`

Template pattern — `phx-update="stream"` on parent, `@streams.name` in comprehension:

```heex
<div id="items" phx-update="stream">
  <div :for={{id, item} <- @streams.items} id={id}>{item.name}</div>
</div>
```

- Streams are not enumerable — to filter, refetch data and re-stream with `reset: true`
- No counting — track counts in a separate assign
- Empty state via CSS: `<div class="hidden only:block">No items yet</div>` as first child
- Never use deprecated `phx-update="append"` or `phx-update="prepend"`

## 6. HEEx Templates

- Always use `~H` sigil or `.html.heex` files — never `~E`
- Interpolation rules:
  - Tag attributes: `{...}` syntax — `<div id={@id}>`
  - Tag bodies (values): `{...}` syntax — `{@my_assign}`
  - Tag bodies (blocks — `if`, `cond`, `case`, `for`): `<%= ... %>` syntax
  - Never use `<%= %>` inside attributes — causes syntax error
- Class lists must use `[...]` syntax with conditional entries:

  ```heex
  <a class={["px-2 text-white", @active && "font-bold", if(@error, do: "border-red-500", else: "border-blue-100")]}>
  ```

- Literal curlies in `<code>`/`<pre>`: annotate with `phx-no-curly-interpolation`
- Never use `<% Enum.each %>` — always `<%= for item <- @items do %>`
- Comments: `<%!-- comment --%>` — always use HEEx comment syntax
- Unique DOM IDs on key elements (forms, buttons, containers) — used in tests

## 7. Forms

Build forms with `to_form/2` and the `<.form>` + `<.input>` components:

```elixir
# In LiveView — from changeset
assign(socket, form: to_form(changeset))

# In LiveView — from params
assign(socket, form: to_form(params, as: :user))
```

```heex
<.form for={@form} id="user-form" phx-change="validate" phx-submit="save">
  <.input field={@form[:name]} type="text" />
</.form>
```

**Forbidden patterns:**
- `<.form for={@changeset}>` — never pass a raw changeset to the template
- `<.form let={f}>` — never use `let` binding; always use `for={@form}` and `@form[:field]`
- `Phoenix.HTML.form_for` / `Phoenix.HTML.inputs_for` — outdated, use `Phoenix.Component` versions

## 8. LiveView Testing

- Use `Phoenix.LiveViewTest` for interaction, `LazyHTML` for assertions
- Reference DOM IDs added to templates: `has_element?(view, "#user-form")`
- Forms: `render_submit/2` and `render_change/2`
- Never test raw HTML — use `element/2`, `has_element?/2`
- Test outcomes, not implementation details — prefer element presence over text content
- Debug selectors with `LazyHTML`:

  ```elixir
  html = render(view)
  document = LazyHTML.from_fragment(html)
  IO.inspect(LazyHTML.filter(document, "#my-selector"), label: "Matches")
  ```

## 9. JS & CSS Integration

- Tailwind v4: no `tailwind.config.js` — use import syntax in `app.css`:

  ```css
  @import "tailwindcss" source(none);
  @source "../css";
  @source "../js";
  @source "../../lib/my_app_web";
  ```

- Never use `@apply` in raw CSS
- Only `app.js` and `app.css` bundles are supported — no external vendor `src`/`href` in layouts
- Import vendor deps into `app.js`/`app.css` — never inline `<script>` or `<link>` tags

## 10. UI/UX Principles

- Subtle micro-interactions: button hover effects, smooth transitions
- Clean typography, spacing, and layout balance
- Delightful details: loading states, hover effects, page transitions
- For design system depth, see `/ux-design`. For responsive patterns, see `/css-responsive`

## 11. Anti-Patterns

| Mistake | Fix |
| --- | --- |
| `list[i]` on Elixir list | `Enum.at(list, i)` |
| `changeset[:field]` | `Ecto.Changeset.get_field(changeset, :field)` |
| `else if` / `elsif` | `cond` or `case` |
| `phx-update="append"` | `phx-update="stream"` with `stream/3` |
| `form_for` / `inputs_for` | `to_form/2` + `<.form for={@form}>` |
| `@changeset` in template | `@form` via `to_form(changeset)` |
| `<.form let={f}>` | `<.form for={@form}>` + `@form[:field]` |
| Nested modules in one file | One module per file |
| `live_redirect` / `live_patch` | `<.link navigate={}>` / `<.link patch={}>` |
| `<script>` in HEEx | JS in `assets/js/`, import in `app.js` |
| `<%= @val %>` in attribute | `{@val}` in attribute |
| `Enum.each` in template | `for` comprehension |
| Raw list assign for collection | `stream/3` |
| `String.to_atom(user_input)` | Validate against known atoms or use strings |
