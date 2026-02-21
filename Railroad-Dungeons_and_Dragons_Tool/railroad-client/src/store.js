import { configureStore } from "@reduxjs/toolkit";
import artifactReducer from "./Artifact/artifactSlice";

export default configureStore({
  reducer: {
    artifact: artifactReducer,
  },
});
