# Backend to Fullstack Bridge

This skill is for Java backend beginners moving toward junior full-stack ability. Teach frontend only as needed for end-to-end feature understanding.

## Focus

Prioritize:

- Controller -> Service -> Mapper -> DB
- DTO, Entity, VO, validation, exception flow
- Vue page -> API call -> Controller -> response rendering
- field naming and mapping across layers
- login token storage, request headers, route guards when needed

Defer:

- advanced CSS
- complex component architecture
- frontend performance
- animation
- advanced state management

## Flow Map

Update `flow-map.md` when a stage changes backend flow, API shape, DTO/VO fields, DB columns, or Vue API calls.

## Field Trace Table

Use this table for full-stack stages:

| Page field | Vue state | API param | DTO field | Service handling | DB column | VO field | Rendered output |
|---|---|---|---|---|---|---|---|

## Beginner Explanation

Explain one concrete chain at a time. For example:

`Login.vue username input -> auth.ts login request -> LoginDTO.username -> AuthService.login -> user.username column -> LoginVO.token -> localStorage token`
