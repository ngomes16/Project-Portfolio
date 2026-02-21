import { createSlice } from "@reduxjs/toolkit";

export const artifactSlice = createSlice({
  name: "artifact",
  initialState: {
    id: null,
    refresh: false,
  },
  reducers: {
    focus: (state, action) => {
      // Redux Toolkit allows us to write "mutating" logic in reducers. It
      // doesn't actually mutate the state because it uses the Immer library,
      // which detects changes to a "draft state" and produces a brand new
      // immutable state based off those changes
      state.id = action.payload;
    },
    refresh: (state, action) => {
      state.refresh = action.payload;
    },
  },
});

export const { focus, refresh } = artifactSlice.actions;

export default artifactSlice.reducer;
