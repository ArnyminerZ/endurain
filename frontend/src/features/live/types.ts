import type { Schemas } from '@/types'

/** What an anonymous viewer of a live share link receives. */
export type PublicLive = Schemas['PublicLiveView']

/** One position update of a live session. */
export type LivePoint = Schemas['LivePointRead']

/** A person emailed the share link when the user starts a live track. */
export type LiveContact = Schemas['LiveContactRead']

/** The fields needed to add a {@link LiveContact}. */
export type LiveContactInput = Schemas['LiveContactCreate']
