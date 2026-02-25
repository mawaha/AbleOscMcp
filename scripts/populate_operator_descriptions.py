"""
Populate Operator parameter database with generated descriptions.

Run with: uv run python scripts/populate_operator_descriptions.py
"""

from ableosc.device_database import DeviceDatabase

OPERATOR_DESCRIPTIONS = {
    # -----------------------------------------------------------------------
    # Global
    # -----------------------------------------------------------------------
    "Device On": (
        "Device On/Off",
        "Enables or disables the entire Operator instrument. When off, no audio is produced."
    ),
    "Algorithm": (
        "FM Algorithm",
        "Selects the routing arrangement between the four oscillators (A, B, C, D). "
        "Operators can act as modulators (affecting another oscillator's frequency) or carriers "
        "(contributing directly to the audio output). Operator provides 11 algorithms covering "
        "series, parallel, and hybrid configurations."
    ),
    "Transpose": (
        "Global Transpose",
        "Shifts the pitch of all oscillators up or down by up to 48 semitones (4 octaves). "
        "Applied globally on top of any per-oscillator coarse tuning."
    ),
    "PB Range": (
        "Pitch Bend Range",
        "Sets the maximum pitch change in semitones when the pitch bend wheel is moved to its "
        "extreme position. A value of 12 means one octave of bend in each direction."
    ),
    "Volume": (
        "Output Volume",
        "Sets the overall output level of the instrument. This is the final gain stage after "
        "all oscillators, envelopes, and the filter."
    ),
    "Panorama": (
        "Panorama",
        "Sets the stereo position of the instrument output. -1.0 is full left, 0.0 is centre, "
        "1.0 is full right."
    ),
    "Pan < Key": (
        "Pan Key Tracking",
        "Determines how much the stereo position shifts with note pitch. Higher values cause "
        "higher notes to pan right and lower notes to pan left, mimicking a real instrument "
        "spread across a stereo field."
    ),
    "Pan < Rnd": (
        "Pan Random",
        "Adds a random offset to the pan position with each new note. Higher values create "
        "wider random panning. Useful for adding stereo movement to chords or arpeggios."
    ),
    "Tone": (
        "Tone",
        "A high-frequency shelving filter applied globally to the output. Higher values add "
        "brightness and presence; lower values give a warmer, darker sound."
    ),
    "Spread": (
        "Unison Spread",
        "Detunes two voices slightly against each other and pans them apart to create a "
        "stereo width effect. 0 is mono; higher values create a wider, chorused sound. "
        "Uses extra CPU when active."
    ),
    "Glide On": (
        "Glide On/Off",
        "Enables portamento — smooth pitch sliding between consecutive notes. When on, "
        "the pitch glides from the previous note to the new one over the time set by Glide Time."
    ),
    "Glide Time": (
        "Glide Time",
        "Sets how long it takes for the pitch to slide from one note to the next when "
        "Glide is enabled. Shorter values give a quick snap; longer values create a slow, "
        "smooth sweep."
    ),

    # -----------------------------------------------------------------------
    # Oscillator A
    # -----------------------------------------------------------------------
    "Osc-A On": (
        "Oscillator A On/Off",
        "Enables or disables Oscillator A. Disabling an oscillator that acts as a carrier "
        "will silence its contribution to the output. Disabling a modulator will remove "
        "its FM effect on downstream oscillators."
    ),
    "A Coarse": (
        "Oscillator A Coarse Tuning",
        "Sets the frequency ratio of Oscillator A relative to the played note in semitone "
        "steps. In FM synthesis this ratio determines the harmonic relationship between "
        "carrier and modulator, directly shaping the timbre."
    ),
    "A Fine": (
        "Oscillator A Fine Tuning",
        "Fine-tunes the frequency of Oscillator A in cents (hundredths of a semitone). "
        "Small detuning between oscillators creates beating and chorus-like effects."
    ),
    "A Freq<Vel": (
        "Oscillator A Frequency Velocity Sensitivity",
        "Controls how much MIDI note velocity shifts the frequency of Oscillator A. "
        "Positive values raise frequency with harder hits; negative values lower it. "
        "In FM synthesis this can create velocity-dependent timbral changes."
    ),
    "A Quantize": (
        "Oscillator A Frequency Quantize",
        "When enabled, locks the oscillator frequency to the nearest integer ratio relative "
        "to the fundamental, ensuring harmonically pure FM relationships."
    ),
    "A Fix On ": (
        "Oscillator A Fixed Frequency On/Off",
        "When enabled, the oscillator frequency is fixed regardless of the played note. "
        "Useful for creating inharmonic spectra or using an oscillator as an LFO-like "
        "modulator at a set frequency."
    ),
    "A Fix Freq": (
        "Oscillator A Fixed Frequency",
        "Sets the absolute frequency of Oscillator A when Fixed Frequency mode is active. "
        "The oscillator will sound at this frequency regardless of the played MIDI note."
    ),
    "A Fix Freq Mul": (
        "Oscillator A Fixed Frequency Multiplier",
        "Multiplies the fixed frequency of Oscillator A by a factor. Combined with "
        "Fix Freq, allows precise tuning of fixed-frequency oscillators across a wide range."
    ),
    "Osc-A Level": (
        "Oscillator A Output Level",
        "Sets the amplitude of Oscillator A. In the context of FM synthesis, this controls "
        "the modulation depth when A is a modulator, or the contribution to the audio "
        "output when A is a carrier."
    ),
    "Osc-A Retrig": (
        "Oscillator A Envelope Retrigger",
        "When enabled, the oscillator envelope restarts from the beginning each time a "
        "new note is played, even if the previous note is still held. When off, legato "
        "playing will not restart the envelope."
    ),
    "Osc-A Phase": (
        "Oscillator A Initial Phase",
        "Sets the starting phase position of Oscillator A's waveform in degrees. "
        "Adjusting phase between oscillators can affect the attack transient and the "
        "character of the initial FM interaction."
    ),
    "Osc-A Lev < Vel": (
        "Oscillator A Level Velocity Sensitivity",
        "Controls how much MIDI velocity affects the output level of Oscillator A. "
        "Positive values make the oscillator louder with harder hits; negative values "
        "make it quieter. Key for dynamics when A is a carrier, or for velocity-sensitive "
        "FM brightness when A is a modulator."
    ),
    "Osc-A Lev < Key": (
        "Oscillator A Level Key Tracking",
        "Scales the output level of Oscillator A based on note pitch. Positive values "
        "increase level for higher notes; negative values decrease it. Useful for "
        "compensating for the natural brightness of high FM tones."
    ),
    "Osc-A Wave": (
        "Oscillator A Waveform",
        "Selects the waveform shape for Oscillator A. Options include sine, sawtooth, "
        "square, triangle, and various noise and digital waveforms. Sine produces pure "
        "FM tones; other waveforms add inherent harmonics before FM is applied."
    ),
    "Osc-A Feedb": (
        "Oscillator A Self-Feedback",
        "Feeds a portion of Oscillator A's output back into its own frequency input. "
        "Low values add subtle harmonic richness; high values produce noise and chaotic "
        "timbres. A classic FM technique for creating distorted or brass-like sounds."
    ),
    "Osc-A < Pe": (
        "Oscillator A Pitch Envelope Depth",
        "Sets how much the pitch envelope modulates the frequency of Oscillator A. "
        "Higher values give a more pronounced pitch sweep over the envelope shape."
    ),
    "Osc-A < LFO": (
        "Oscillator A LFO Depth",
        "Sets how much the LFO modulates the frequency of Oscillator A. Creates vibrato "
        "at audio-rate or gentle pitch wobble at low LFO rates."
    ),

    # -----------------------------------------------------------------------
    # Oscillator A Envelope
    # -----------------------------------------------------------------------
    "Ae Attack": (
        "Oscillator A Envelope Attack",
        "Sets the time for Oscillator A's amplitude envelope to rise from silence (or the "
        "initial level) to its peak level after a note is triggered."
    ),
    "Ae Init": (
        "Oscillator A Envelope Initial Level",
        "Sets the level at which Oscillator A's envelope begins when a note is triggered, "
        "before the attack phase. 0 starts from silence; higher values begin louder."
    ),
    "Ae Decay": (
        "Oscillator A Envelope Decay",
        "Sets the time for Oscillator A's envelope to fall from its peak level to the "
        "sustain level after the attack phase completes."
    ),
    "Ae Peak": (
        "Oscillator A Envelope Peak Level",
        "Sets the maximum level reached at the top of the attack phase before the "
        "envelope begins its decay."
    ),
    "Ae Sustain": (
        "Oscillator A Envelope Sustain Level",
        "Sets the level at which Oscillator A's envelope holds while a note is held down, "
        "after the decay phase has completed."
    ),
    "Ae Release": (
        "Oscillator A Envelope Release",
        "Sets the time for Oscillator A's envelope to fade from the sustain level to "
        "silence after a note is released."
    ),
    "Ae Mode": (
        "Oscillator A Envelope Mode",
        "Selects the envelope behaviour mode: standard ADSR, looping (the envelope "
        "repeats while the note is held), or other cycling modes for rhythmic amplitude "
        "modulation effects."
    ),
    "Ae Loop": (
        "Oscillator A Envelope Loop",
        "When enabled, the envelope loops between the decay and sustain stages while "
        "the note is held, creating a rhythmic or tremolo-like amplitude effect."
    ),
    "Ae Retrig": (
        "Oscillator A Envelope Retrigger Mode",
        "Sets how the envelope responds when a new note is played while one is held. "
        "Options include always retrigger, only retrigger on new notes (legato), and "
        "various beat-synced retrigger intervals."
    ),
    "Ae R < Vel": (
        "Oscillator A Envelope Release Velocity Sensitivity",
        "Scales the release time of Oscillator A's envelope based on note velocity. "
        "Positive values give faster release for harder hits; negative values give slower release."
    ),

    # -----------------------------------------------------------------------
    # Oscillator B  (identical structure to A — abbreviated)
    # -----------------------------------------------------------------------
    "Osc-B On": ("Oscillator B On/Off", "Enables or disables Oscillator B."),
    "B Coarse": ("Oscillator B Coarse Tuning", "Sets the frequency ratio of Oscillator B in semitone steps relative to the played note."),
    "B Fine": ("Oscillator B Fine Tuning", "Fine-tunes Oscillator B in cents. Small offsets from A create beating and stereo width."),
    "B Freq<Vel": ("Oscillator B Frequency Velocity Sensitivity", "Controls how much note velocity shifts the frequency of Oscillator B."),
    "B Quantize": ("Oscillator B Frequency Quantize", "Locks Oscillator B to the nearest integer frequency ratio for harmonic FM relationships."),
    "B Fix On ": ("Oscillator B Fixed Frequency On/Off", "When enabled, Oscillator B plays at a fixed frequency regardless of the played note."),
    "B Fix Freq": ("Oscillator B Fixed Frequency", "Sets the absolute frequency of Oscillator B when Fixed Frequency mode is active."),
    "B Fix Freq Mul": ("Oscillator B Fixed Frequency Multiplier", "Multiplies the fixed frequency of Oscillator B by a factor."),
    "Osc-B Level": ("Oscillator B Output Level", "Sets the amplitude of Oscillator B — modulation depth if B is a modulator, or output level if it is a carrier."),
    "Osc-B Retrig": ("Oscillator B Envelope Retrigger", "When enabled, Oscillator B's envelope restarts from the beginning on each new note."),
    "Osc-B Phase": ("Oscillator B Initial Phase", "Sets the starting phase position of Oscillator B's waveform in degrees."),
    "Osc-B Lev < Vel": ("Oscillator B Level Velocity Sensitivity", "Controls how much MIDI velocity affects the output level of Oscillator B."),
    "Osc-B Lev < Key": ("Oscillator B Level Key Tracking", "Scales the output level of Oscillator B based on note pitch."),
    "Osc-B Wave": ("Oscillator B Waveform", "Selects the waveform for Oscillator B: sine, saw, square, triangle, noise, or digital waveforms."),
    "Osc-B Feedb": ("Oscillator B Self-Feedback", "Feeds a portion of Oscillator B's output back into its own frequency input for added harmonic complexity."),
    "Osc-B < Pe": ("Oscillator B Pitch Envelope Depth", "Sets how much the pitch envelope modulates the frequency of Oscillator B."),
    "Osc-B < LFO": ("Oscillator B LFO Depth", "Sets how much the LFO modulates the frequency of Oscillator B."),
    "Be Attack": ("Oscillator B Envelope Attack", "Time for Oscillator B's envelope to rise from initial to peak level."),
    "Be Init": ("Oscillator B Envelope Initial Level", "Starting level of Oscillator B's envelope when a note is triggered."),
    "Be Decay": ("Oscillator B Envelope Decay", "Time for Oscillator B's envelope to fall from peak to sustain level."),
    "Be Peak": ("Oscillator B Envelope Peak Level", "Maximum level reached at the top of Oscillator B's attack phase."),
    "Be Sustain": ("Oscillator B Envelope Sustain Level", "Level held by Oscillator B's envelope while the note is held after decay."),
    "Be Release": ("Oscillator B Envelope Release", "Time for Oscillator B's envelope to fade to silence after note release."),
    "Be Mode": ("Oscillator B Envelope Mode", "Selects standard ADSR or looping/cycling envelope modes for Oscillator B."),
    "Be Loop": ("Oscillator B Envelope Loop", "When enabled, Oscillator B's envelope loops between decay and sustain while the note is held."),
    "Be Retrig": ("Oscillator B Envelope Retrigger Mode", "Sets how Oscillator B's envelope responds when a new note is played while one is held."),
    "Be R < Vel": ("Oscillator B Envelope Release Velocity Sensitivity", "Scales Oscillator B's release time based on note velocity."),

    # -----------------------------------------------------------------------
    # Oscillator C
    # -----------------------------------------------------------------------
    "Osc-C On": ("Oscillator C On/Off", "Enables or disables Oscillator C."),
    "C Coarse": ("Oscillator C Coarse Tuning", "Sets the frequency ratio of Oscillator C in semitone steps relative to the played note."),
    "C Fine": ("Oscillator C Fine Tuning", "Fine-tunes Oscillator C in cents."),
    "C Freq<Vel": ("Oscillator C Frequency Velocity Sensitivity", "Controls how much note velocity shifts the frequency of Oscillator C."),
    "C Quantize": ("Oscillator C Frequency Quantize", "Locks Oscillator C to the nearest integer frequency ratio."),
    "C Fix On ": ("Oscillator C Fixed Frequency On/Off", "When enabled, Oscillator C plays at a fixed frequency regardless of pitch."),
    "C Fix Freq": ("Oscillator C Fixed Frequency", "Sets the absolute frequency of Oscillator C in fixed frequency mode."),
    "C Fix Freq Mul": ("Oscillator C Fixed Frequency Multiplier", "Multiplies the fixed frequency of Oscillator C by a factor."),
    "Osc-C Level": ("Oscillator C Output Level", "Sets the amplitude of Oscillator C."),
    "Osc-C Retrig": ("Oscillator C Envelope Retrigger", "When enabled, Oscillator C's envelope restarts on each new note."),
    "Osc-C Phase": ("Oscillator C Initial Phase", "Sets the starting phase of Oscillator C's waveform in degrees."),
    "Osc-C Lev < Vel": ("Oscillator C Level Velocity Sensitivity", "Controls how much MIDI velocity affects Oscillator C's output level."),
    "Osc-C Lev < Key": ("Oscillator C Level Key Tracking", "Scales Oscillator C's output level based on note pitch."),
    "Osc-C Wave": ("Oscillator C Waveform", "Selects the waveform for Oscillator C."),
    "Osc-C Feedb": ("Oscillator C Self-Feedback", "Feeds Oscillator C's output back into its own frequency input."),
    "Osc-C < Pe": ("Oscillator C Pitch Envelope Depth", "Sets how much the pitch envelope modulates Oscillator C's frequency."),
    "Osc-C < LFO": ("Oscillator C LFO Depth", "Sets how much the LFO modulates Oscillator C's frequency."),
    "Ce Attack": ("Oscillator C Envelope Attack", "Time for Oscillator C's envelope to rise to peak level."),
    "Ce Init": ("Oscillator C Envelope Initial Level", "Starting level of Oscillator C's envelope on note trigger."),
    "Ce Decay": ("Oscillator C Envelope Decay", "Time for Oscillator C's envelope to fall from peak to sustain."),
    "Ce Peak": ("Oscillator C Envelope Peak Level", "Maximum level at the top of Oscillator C's attack."),
    "Ce Sustain": ("Oscillator C Envelope Sustain Level", "Level held by Oscillator C's envelope while note is held."),
    "Ce Release": ("Oscillator C Envelope Release", "Time for Oscillator C's envelope to fade after note release."),
    "Ce Mode": ("Oscillator C Envelope Mode", "Selects standard or looping envelope mode for Oscillator C."),
    "Ce Loop": ("Oscillator C Envelope Loop", "When enabled, Oscillator C's envelope loops between decay and sustain."),
    "Ce Retrig": ("Oscillator C Envelope Retrigger Mode", "Sets how Oscillator C's envelope responds to new notes while one is held."),
    "Ce R < Vel": ("Oscillator C Envelope Release Velocity Sensitivity", "Scales Oscillator C's release time based on note velocity."),

    # -----------------------------------------------------------------------
    # Oscillator D
    # -----------------------------------------------------------------------
    "Osc-D On": ("Oscillator D On/Off", "Enables or disables Oscillator D."),
    "D Coarse": ("Oscillator D Coarse Tuning", "Sets the frequency ratio of Oscillator D in semitone steps relative to the played note."),
    "D Fine": ("Oscillator D Fine Tuning", "Fine-tunes Oscillator D in cents."),
    "D Freq<Vel": ("Oscillator D Frequency Velocity Sensitivity", "Controls how much note velocity shifts the frequency of Oscillator D."),
    "D Quantize": ("Oscillator D Frequency Quantize", "Locks Oscillator D to the nearest integer frequency ratio."),
    "D Fix On ": ("Oscillator D Fixed Frequency On/Off", "When enabled, Oscillator D plays at a fixed frequency regardless of pitch."),
    "D Fix Freq": ("Oscillator D Fixed Frequency", "Sets the absolute frequency of Oscillator D in fixed frequency mode."),
    "D Fix Freq Mul": ("Oscillator D Fixed Frequency Multiplier", "Multiplies the fixed frequency of Oscillator D by a factor."),
    "Osc-D Level": ("Oscillator D Output Level", "Sets the amplitude of Oscillator D."),
    "Osc-D Retrig": ("Oscillator D Envelope Retrigger", "When enabled, Oscillator D's envelope restarts on each new note."),
    "Osc-D Phase": ("Oscillator D Initial Phase", "Sets the starting phase of Oscillator D's waveform in degrees."),
    "Osc-D Lev < Vel": ("Oscillator D Level Velocity Sensitivity", "Controls how much MIDI velocity affects Oscillator D's output level."),
    "Osc-D Lev < Key": ("Oscillator D Level Key Tracking", "Scales Oscillator D's output level based on note pitch."),
    "Osc-D Wave": ("Oscillator D Waveform", "Selects the waveform for Oscillator D."),
    "Osc-D Feedb": ("Oscillator D Self-Feedback", "Feeds Oscillator D's output back into its own frequency input."),
    "Osc-D < Pe": ("Oscillator D Pitch Envelope Depth", "Sets how much the pitch envelope modulates Oscillator D's frequency."),
    "Osc-D < LFO": ("Oscillator D LFO Depth", "Sets how much the LFO modulates Oscillator D's frequency."),
    "De Attack": ("Oscillator D Envelope Attack", "Time for Oscillator D's envelope to rise to peak level."),
    "De Init": ("Oscillator D Envelope Initial Level", "Starting level of Oscillator D's envelope on note trigger."),
    "De Decay": ("Oscillator D Envelope Decay", "Time for Oscillator D's envelope to fall from peak to sustain."),
    "De Peak": ("Oscillator D Envelope Peak Level", "Maximum level at the top of Oscillator D's attack."),
    "De Sustain": ("Oscillator D Envelope Sustain Level", "Level held by Oscillator D's envelope while note is held."),
    "De Release": ("Oscillator D Envelope Release", "Time for Oscillator D's envelope to fade after note release."),
    "De Mode": ("Oscillator D Envelope Mode", "Selects standard or looping envelope mode for Oscillator D."),
    "De Loop": ("Oscillator D Envelope Loop", "When enabled, Oscillator D's envelope loops between decay and sustain."),
    "De Retrig": ("Oscillator D Envelope Retrigger Mode", "Sets how Oscillator D's envelope responds to new notes while one is held."),
    "De R < Vel": ("Oscillator D Envelope Release Velocity Sensitivity", "Scales Oscillator D's release time based on note velocity."),

    # -----------------------------------------------------------------------
    # Global Time / Pitch Envelope
    # -----------------------------------------------------------------------
    "Time": (
        "Global Envelope Time Scaling",
        "Scales all envelope times (attack, decay, release) across all oscillators "
        "simultaneously. Positive values lengthen all envelopes; negative values shorten them. "
        "A quick way to change the overall articulation without touching individual envelopes."
    ),
    "Time < Key": (
        "Envelope Time Key Tracking",
        "Scales all envelope times based on note pitch. Negative values make higher notes "
        "decay faster, mimicking the natural behaviour of acoustic instruments where higher "
        "notes decay more quickly."
    ),
    "Pe On": (
        "Pitch Envelope On/Off",
        "Enables the global pitch envelope. When active, the envelope modulates the "
        "frequency of all oscillators (or selected ones) over time, creating pitch sweeps "
        "on note attack, release, or throughout the note."
    ),
    "Pe Attack": (
        "Pitch Envelope Attack",
        "Sets the time for the pitch envelope to move from its initial value to its peak "
        "value. Short attacks create sharp pitch transients; longer attacks give a slow "
        "pitch rise into the note."
    ),
    "Pe Init": (
        "Pitch Envelope Initial Level",
        "Sets the pitch offset (in semitones) at the moment a note is triggered, before "
        "the attack phase. Negative values start the pitch below the target; positive "
        "values start above."
    ),
    "Pe A Slope": (
        "Pitch Envelope Attack Slope",
        "Controls the curvature of the pitch envelope's attack segment. Negative values "
        "create a convex curve (fast initial movement, slow approach to peak); positive "
        "values create a concave curve (slow start, fast approach)."
    ),
    "Pe Decay": (
        "Pitch Envelope Decay",
        "Sets the time for the pitch envelope to move from its peak value to its sustain "
        "level after the attack phase."
    ),
    "Pe Peak": (
        "Pitch Envelope Peak Level",
        "Sets the pitch offset (in semitones) at the top of the attack phase — the "
        "maximum pitch deviation before the envelope decays to sustain."
    ),
    "Pe D Slope": (
        "Pitch Envelope Decay Slope",
        "Controls the curvature of the pitch envelope's decay segment."
    ),
    "Pe Sustain": (
        "Pitch Envelope Sustain Level",
        "Sets the pitch offset (in semitones) held while the note is sustained after "
        "the decay phase. 0 means no pitch offset during sustain."
    ),
    "Pe Release": (
        "Pitch Envelope Release",
        "Sets the time for the pitch envelope to return to zero after a note is released."
    ),
    "Pe End": (
        "Pitch Envelope End Level",
        "Sets the final pitch offset (in semitones) at the end of the release phase. "
        "Allows the pitch to land at a different value than zero after the note ends."
    ),
    "Pe R Slope": (
        "Pitch Envelope Release Slope",
        "Controls the curvature of the pitch envelope's release segment."
    ),
    "Pe Mode": (
        "Pitch Envelope Mode",
        "Selects the behaviour of the pitch envelope: standard one-shot, looping, or "
        "other cycling modes for creating rhythmic pitch effects."
    ),
    "Pe Loop": (
        "Pitch Envelope Loop",
        "When enabled, the pitch envelope loops between its decay and sustain stages "
        "while the note is held, creating a cycling pitch modulation effect."
    ),
    "Pe Retrig": (
        "Pitch Envelope Retrigger Mode",
        "Sets how the pitch envelope responds when a new note is played while one is held."
    ),
    "Pe R < Vel": (
        "Pitch Envelope Release Velocity Sensitivity",
        "Scales the release time of the pitch envelope based on note velocity."
    ),
    "Pe Amount": (
        "Pitch Envelope Amount — Primary Destination",
        "Sets the overall depth of the pitch envelope's effect on the primary modulation "
        "destination (typically all oscillator frequencies). Higher values create more "
        "pronounced pitch sweeps."
    ),
    "Pe Amt A": (
        "Pitch Envelope Amount A",
        "Sets how much the pitch envelope modulates the primary destination (usually all "
        "oscillator frequencies). Expressed as a percentage."
    ),
    "Pe Dst B": (
        "Pitch Envelope Destination B",
        "Selects a secondary modulation destination for the pitch envelope. Allows the "
        "envelope to simultaneously modulate a different parameter alongside pitch — "
        "for example, filter frequency or oscillator level."
    ),
    "Pe Amt B": (
        "Pitch Envelope Amount B",
        "Sets how much the pitch envelope modulates the secondary destination (Pe Dst B). "
        "Can be positive (increase) or negative (decrease)."
    ),

    # -----------------------------------------------------------------------
    # LFO
    # -----------------------------------------------------------------------
    "LFO On": (
        "LFO On/Off",
        "Enables or disables the LFO (Low Frequency Oscillator). The LFO generates a "
        "slow cyclic modulation signal used to add vibrato, tremolo, or other periodic "
        "movement to oscillator frequencies, levels, or the filter."
    ),
    "LFO Type": (
        "LFO Waveform",
        "Selects the shape of the LFO waveform: sine (smooth), triangle, sawtooth up, "
        "sawtooth down, square, sample-and-hold (random steps), or random smooth. "
        "Different shapes produce different modulation characters."
    ),
    "LFO Range": (
        "LFO Rate Range",
        "Sets the overall frequency range of the LFO: Low (sub-Hz, deep and slow), "
        "High (up to audio rates for FM-style effects), or Sync (tempo-synced). "
        "Switching to High allows the LFO to act as an additional FM oscillator."
    ),
    "LFO Rate": (
        "LFO Rate",
        "Sets the speed of the LFO. In Low/High range this is a frequency value; "
        "in Sync mode this selects a note division. Slower rates create gentle movement; "
        "faster rates produce vibrato or tremolo."
    ),
    "LFO Sync": (
        "LFO Sync Division",
        "When LFO Range is set to Sync, this selects the rhythmic division to lock "
        "the LFO rate to (e.g. 1/4, 1/8, 1/16). The LFO will cycle in time with the "
        "project tempo."
    ),
    "LFO R < K": (
        "LFO Rate Key Tracking",
        "Scales the LFO rate based on note pitch when enabled. Higher notes get a "
        "faster LFO, lower notes get a slower one — mimicking the natural vibrato "
        "characteristics of acoustic instruments."
    ),
    "LFO Retrigger": (
        "LFO Retrigger",
        "When enabled, the LFO resets to the start of its waveform cycle with each "
        "new note. When off, the LFO runs freely and continuously regardless of "
        "note triggers, giving a more random, evolving character."
    ),
    "LFO Amt": (
        "LFO Amount",
        "Sets the overall depth of the LFO modulation. At zero there is no effect; "
        "higher values produce stronger modulation of the selected destinations."
    ),
    "LFO Amt A": (
        "LFO Amount — Primary Destination",
        "Sets how much the LFO modulates the primary destination. This controls the "
        "depth of vibrato, tremolo, or filter movement depending on which oscillators "
        "and the filter are set to respond to the LFO."
    ),
    "LFO Dst B": (
        "LFO Destination B",
        "Selects a secondary modulation destination for the LFO, allowing it to "
        "simultaneously affect a different parameter alongside the primary LFO targets "
        "set per oscillator and on the filter."
    ),
    "LFO Amt B": (
        "LFO Amount B",
        "Sets how much the LFO modulates the secondary destination (LFO Dst B)."
    ),
    "LFO < Vel": (
        "LFO Velocity Sensitivity",
        "Controls how much MIDI note velocity scales the LFO depth. Positive values "
        "increase LFO modulation with harder hits (useful for adding vibrato to "
        "accented notes); negative values decrease it."
    ),
    "LFO < Pe": (
        "LFO Pitch Envelope Depth",
        "Sets how much the pitch envelope modulates the LFO rate. Allows the LFO "
        "speed to change over the course of a note following the pitch envelope shape."
    ),

    # -----------------------------------------------------------------------
    # LFO Envelope
    # -----------------------------------------------------------------------
    "Le Attack": (
        "LFO Envelope Attack",
        "Sets the time for the LFO envelope to rise from silence to full depth. "
        "Used to create a gradual LFO fade-in — for example, vibrato that builds "
        "slowly after a note is struck."
    ),
    "Le Init": ("LFO Envelope Initial Level", "Starting level of the LFO envelope on note trigger."),
    "Le Decay": ("LFO Envelope Decay", "Time for the LFO envelope to fall from peak to sustain level."),
    "Le Peak": ("LFO Envelope Peak Level", "Maximum level reached at the top of the LFO envelope attack."),
    "Le Sustain": ("LFO Envelope Sustain Level", "Level at which the LFO envelope holds while the note is sustained."),
    "Le Release": ("LFO Envelope Release", "Time for the LFO envelope to fade after note release."),
    "Le End": ("LFO Envelope End Level", "Final level of the LFO envelope at the end of the release phase."),
    "Le Mode": ("LFO Envelope Mode", "Selects standard ADSR or looping/cycling modes for the LFO envelope."),
    "Le Loop": ("LFO Envelope Loop", "When enabled, the LFO envelope loops between decay and sustain while the note is held."),
    "Le Retrig": ("LFO Envelope Retrigger Mode", "Sets how the LFO envelope responds when a new note is played while one is held."),
    "Le R < Vel": ("LFO Envelope Release Velocity Sensitivity", "Scales the LFO envelope release time based on note velocity."),

    # -----------------------------------------------------------------------
    # Filter
    # -----------------------------------------------------------------------
    "Filter On": (
        "Filter On/Off",
        "Enables or disables Operator's multimode filter. When off, all oscillator "
        "output passes through unfiltered. Disabling the filter saves CPU."
    ),
    "Filter Type": (
        "Filter Type",
        "Selects the filter topology: Low-pass (removes high frequencies), High-pass "
        "(removes low frequencies), Band-pass (passes a band of frequencies), Notch "
        "(removes a band), or Morph (smoothly transitions between types via Filter Morph)."
    ),
    "Filter Circuit - LP/HP": (
        "Filter Circuit — Low-Pass / High-Pass",
        "Selects the filter circuit design for LP and HP modes. Options include clean "
        "digital designs and analogue-modelled circuits (Moog ladder, MS-20 style) that "
        "impart different characters — from transparent to warm and saturated."
    ),
    "Filter Circuit - BP/NO/Morph": (
        "Filter Circuit — Band-Pass / Notch / Morph",
        "Selects the filter circuit design for BP, Notch, and Morph filter types."
    ),
    "Filter Slope": (
        "Filter Slope",
        "Sets the steepness of the filter's frequency cutoff: 12dB/octave (2-pole, "
        "gentler rolloff) or 24dB/octave (4-pole, steeper and more pronounced). "
        "24dB gives a stronger filter effect with more resonant character."
    ),
    "Filter Freq": (
        "Filter Frequency",
        "This defines the center or cutoff frequency of the filter. Note that the "
        "resulting frequency may also be modulated by note velocity and by the filter envelope."
    ),
    "Filter Res": (
        "Filter Resonance",
        "Sets the resonance (Q) of the filter — the emphasis applied at the cutoff "
        "frequency. Higher values create a distinctive peak or ringing at the cutoff "
        "point. At very high values with some circuit types the filter will self-oscillate, "
        "producing a sine-wave tone."
    ),
    "Filter Morph": (
        "Filter Morph",
        "When Filter Type is set to Morph, this continuously blends between LP, BP, "
        "and HP filter responses. At 0 the filter is fully LP; at 0.5 it is BP; "
        "at 1.0 it is fully HP. Can be modulated for dynamic filter sweeps."
    ),
    "Filter Drive": (
        "Filter Drive",
        "Applies input gain before the filter stage, driving the filter circuit into "
        "saturation. Adds harmonic warmth and distortion, with the character varying "
        "depending on the selected filter circuit."
    ),
    "Filt < Vel": (
        "Filter Frequency Velocity Sensitivity",
        "Controls how much MIDI note velocity opens or closes the filter. Positive "
        "values raise the filter frequency with harder hits (brighter on accents); "
        "negative values lower it."
    ),
    "Filt < Key": (
        "Filter Frequency Key Tracking",
        "Scales the filter cutoff frequency based on note pitch. A value of 100% means "
        "the cutoff tracks pitch one-to-one, keeping the filter character consistent "
        "across the keyboard. Lower values apply less tracking."
    ),
    "Fe Amount": (
        "Filter Envelope Amount",
        "Sets how much the filter envelope modulates the filter frequency. Positive "
        "values open the filter during the envelope; negative values close it. "
        "This is the primary control for classic envelope filter sweeps."
    ),
    "Filt < LFO": (
        "Filter LFO Depth",
        "Sets how much the LFO modulates the filter frequency. Creates cyclic filter "
        "movement — from subtle wah-like effects at slow LFO rates to dramatic sweeps "
        "at faster rates."
    ),

    # -----------------------------------------------------------------------
    # Filter Envelope
    # -----------------------------------------------------------------------
    "Fe Attack": (
        "Filter Envelope Attack",
        "Sets the time for the filter envelope to rise from its initial frequency "
        "offset to its peak. Short attacks create a sharp filter opening on note "
        "onset; longer attacks give a slow swell."
    ),
    "Fe Init": (
        "Filter Envelope Initial Level",
        "Sets the filter frequency offset at the moment a note is triggered, before "
        "the attack begins."
    ),
    "Fe A Slope": (
        "Filter Envelope Attack Slope",
        "Controls the curvature of the filter envelope's attack segment — how the "
        "filter opens over the attack time."
    ),
    "Fe Decay": (
        "Filter Envelope Decay",
        "Sets the time for the filter envelope to move from its peak back toward "
        "the sustain level after the attack phase."
    ),
    "Fe Peak": (
        "Filter Envelope Peak Level",
        "Sets the maximum filter frequency offset at the top of the envelope attack "
        "before decay begins."
    ),
    "Fe D Slope": (
        "Filter Envelope Decay Slope",
        "Controls the curvature of the filter envelope's decay segment."
    ),
    "Fe Sustain": (
        "Filter Envelope Sustain Level",
        "Sets the filter frequency offset maintained while the note is held after "
        "the decay phase."
    ),
    "Fe Release": (
        "Filter Envelope Release",
        "Sets the time for the filter envelope to return to zero after the note is released."
    ),
    "Fe End": (
        "Filter Envelope End Level",
        "Sets the filter frequency offset at the very end of the release phase."
    ),
    "Fe R Slope": (
        "Filter Envelope Release Slope",
        "Controls the curvature of the filter envelope's release segment."
    ),
    "Fe Mode": (
        "Filter Envelope Mode",
        "Selects standard ADSR or looping/cycling modes for the filter envelope."
    ),
    "Fe Loop": (
        "Filter Envelope Loop",
        "When enabled, the filter envelope loops between decay and sustain while the "
        "note is held, creating a rhythmic filter effect."
    ),
    "Fe Retrig": (
        "Filter Envelope Retrigger Mode",
        "Sets how the filter envelope responds when a new note is played while one is held."
    ),
    "Fe R < Vel": (
        "Filter Envelope Release Velocity Sensitivity",
        "Scales the filter envelope's release time based on note velocity."
    ),

    # -----------------------------------------------------------------------
    # Shaper
    # -----------------------------------------------------------------------
    "Shaper Type": (
        "Shaper Type",
        "Selects the waveshaping distortion algorithm applied after the filter. Options "
        "include soft clip, hard clip, sine fold, and other nonlinear curves. Each adds "
        "a different harmonic character — from subtle warmth to aggressive distortion."
    ),
    "Shaper Mix": (
        "Shaper Mix",
        "Sets the blend between the dry (unprocessed) and shaped (distorted) signal. "
        "At 0% no distortion is applied; at 100% only the shaped signal is heard. "
        "Intermediate values allow parallel distortion blending."
    ),
    "Shaper Drive": (
        "Shaper Drive",
        "Sets the input gain into the shaper stage. Higher drive values push more of "
        "the signal into the nonlinear region of the selected waveshaper curve, "
        "increasing harmonic content and apparent loudness."
    ),
}


def main():
    db = DeviceDatabase()
    entry = db.get_device("Operator")
    if entry is None:
        print("ERROR: Operator not found in database. Run catalog_device first.")
        return

    annotated = 0
    skipped = 0

    for param in entry.parameters:
        name = param.name
        if name in OPERATOR_DESCRIPTIONS:
            title, text = OPERATOR_DESCRIPTIONS[name]
            db.annotate_parameter("Operator", param.index, title, text)
            annotated += 1
        else:
            skipped += 1
            print(f"  NO DESC: [{param.index}] {name!r}")

    print(f"\nAnnotated: {annotated} / {len(entry.parameters)} parameters")
    if skipped:
        print(f"Skipped:   {skipped} (no description generated)")

    # Verify Filter Freq
    results = db.lookup_parameter("Operator", "Filter Freq")
    p = results[0]
    print(f"\nSample — [{p['index']}] {p['name']}")
    print(f"  Title: {p['info_title']}")
    print(f"  Text:  {p['info_text'][:80]}...")


if __name__ == "__main__":
    main()
