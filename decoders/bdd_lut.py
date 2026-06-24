"""BDD/decode-LUT placeholder for future component decoder experiments."""


class BDDLUTDecoder:
    """Bounded-distance decoder LUT interface placeholder."""

    def decode(self, syndrome):
        """Decode one syndrome into a correction pattern."""
        raise NotImplementedError("BDDLUTDecoder.decode will be implemented later")
